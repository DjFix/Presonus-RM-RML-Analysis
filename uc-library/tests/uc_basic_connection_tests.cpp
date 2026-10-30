#include "presonus/uc/basic_connection.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
using namespace Presonus::UC;
constexpr unsigned size = 1216;
using Image = std::array<unsigned char, size>;
static std::uint32_t word(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static std::uint32_t readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  if (!f)
    std::abort();
  return word(b.data());
}
static void put(Image &b, unsigned off, std::uint32_t v, unsigned n = 4) {
  for (unsigned i = 0; i < n; ++i)
    b[off + i] = static_cast<unsigned char>(v >> (8 * i));
}
static ParamValueEvent load(const Image &b) {
  ParamValueEvent v;
  v.header = {word(b.data()), word(b.data() + 4), word(b.data() + 8),
              word(b.data() + 12)};
  std::memcpy(v.path.data(), b.data() + 16, 128);
  v.index = static_cast<unsigned short>(b[144] | (unsigned(b[145]) << 8));
  std::memcpy(v.reserved92.data(), b.data() + 146, 2);
  v.valueBits = word(b.data() + 148);
  return v;
}
static Image save(const ParamValueEvent &v, Image b) {
  put(b, 0, v.header.type);
  put(b, 4, v.header.reserved04);
  put(b, 8, v.header.routeA);
  put(b, 12, v.header.routeB);
  std::memcpy(b.data() + 16, v.path.data(), 128);
  put(b, 144, v.index, 2);
  std::memcpy(b.data() + 146, v.reserved92.data(), 2);
  put(b, 148, v.valueBits);
  return b;
}
struct Context;
struct Item : EventItem {
  Context *context;
  unsigned id;
  ParamValueEvent value;
  Image original;
  Item(Context *c, unsigned i, const Image &b)
      : context(c), id(i), value(load(b)), original(b) {}
  ~Item() override;
  Event &getData() override;
};
struct Context {
  std::array<Item *, 4> items{};
  std::array<presonus::uc::EventQueueNode, 4> nodes{};
  std::array<unsigned, 4> previous{0xffffffffu, 0xffffffffu, 0xffffffffu,
                                   0xffffffffu};
  std::array<unsigned, 4> destroyed{};
  presonus::uc::EventQueueNode *tail = nullptr;
  presonus::uc::EventQueueState *state = nullptr;
  ParamValueEvent source;
  Image sourceOriginal{};
  bool held = false, invalid = false, recording = true, cloneNull = false;
  unsigned cloneCalls = 0;
  std::vector<unsigned char> trace;
  ParamValueEvent &resolve(const Event &event) {
    if (&source.header == &event)
      return source;
    for (auto *i : items)
      if (i && &i->value.header == &event)
        return i->value;
    std::abort();
  }
  unsigned nodeID(const presonus::uc::EventQueueNode *node) {
    if (!node)
      return 0xffffffffu;
    for (unsigned i = 0; i < 4; ++i)
      if (node == &nodes[i])
        return i;
    std::abort();
  }
};
Item::~Item() {
  if (context->recording) {
    if (context->held)
      context->invalid = true;
    context->trace.push_back(static_cast<unsigned char>(32 + id));
    ++context->destroyed[id];
  }
  context->items[id] = nullptr;
}
Event &Item::getData() {
  if (!context->held && id != 2)
    context->invalid = true;
  context->trace.push_back(static_cast<unsigned char>(16 + id));
  return value.header;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 8> magic{};
  f.read(reinterpret_cast<char *>(magic.data()), 8);
  if (std::memcmp(magic.data(), "UCBAv001", 8))
    return 3;
  unsigned records = readWord(f);
  for (unsigned record = 0; record < records; ++record) {
    unsigned op = readWord(f), n = readWord(f), reverse = readWord(f),
             fallback = readWord(f), cloneNull = readWord(f),
             itemNull = readWord(f), expectedResult = readWord(f),
             traceLength = readWord(f);
    if (op > 2 || n > 2 || traceLength > 32)
      return 4;
    std::array<unsigned char, 32> trace{};
    f.read(reinterpret_cast<char *>(trace.data()), trace.size());
    std::array<std::uint32_t, 19> small{};
    for (auto &v : small)
      v = readWord(f);
    std::array<Image, 5> before{};
    for (auto &b : before)
      f.read(reinterpret_cast<char *>(b.data()), b.size());
    if (!f)
      return 5;
    auto expected = before;
    unsigned runs = readWord(f), lastEnd = 0;
    for (unsigned i = 0; i < runs; ++i) {
      unsigned start = readWord(f), length = readWord(f);
      if (start < lastEnd || start + length > 5 * size)
        return 6;
      for (unsigned j = 0; j < length; ++j) {
        char ch;
        f.get(ch);
        expected[(start + j) / size][(start + j) % size] =
            static_cast<unsigned char>(ch);
      }
      lastEnd = start + length;
    }
    Context c;
    c.sourceOriginal = before[0];
    c.source = load(before[0]);
    c.cloneNull = cloneNull;
    for (unsigned i = 0; i < 3; ++i) {
      c.items[i] = new Item(&c, i, before[i + 1]);
      c.nodes[i].item = c.items[i];
    }
    presonus::uc::EventQueueState storage;
    storage.context = &c;
    c.state = &storage;
    std::vector<unsigned> order;
    for (unsigned i = 0; i < n; ++i)
      order.push_back(i);
    if (reverse)
      std::reverse(order.begin(), order.end());
    for (unsigned i = 0; i < n; ++i) {
      c.nodes[order[i]].next = i + 1 < n ? &c.nodes[order[i + 1]] : nullptr;
      c.previous[order[i]] = i ? order[i - 1] : 0xffffffffu;
    }
    storage.head = n ? &c.nodes[order.front()] : nullptr;
    c.tail = n ? &c.nodes[order.back()] : nullptr;
    storage.lock = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      if (c.held)
        c.invalid = true;
      c.held = true;
      c.trace.push_back(1);
    };
    storage.unlock = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      if (!c.held)
        c.invalid = true;
      c.held = false;
      c.trace.push_back(2);
    };
    storage.value = [](void *p, const Event &e,
                       presonus::uc::QueueValueKind kind) -> void * {
      auto &c = *static_cast<Context *>(p);
      if (!c.held || kind != presonus::uc::QueueValueKind::Value)
        std::abort();
      return &c.resolve(e);
    };
    EventQueue queue(storage);
    presonus::uc::FactoryRegistry registry;
    presonus::uc::FactoryCodec codec;
    codec.context = &c;
    codec.clone = [](void *p, const Event &e) -> EventItem * {
      auto &c = *static_cast<Context *>(p);
      if (c.held)
        c.invalid = true;
      c.trace.push_back(64);
      ++c.cloneCalls;
      if (c.cloneNull)
        return nullptr;
      Image b{};
      b = save(c.resolve(e), b);
      auto *item = new Item(&c, 3, b);
      c.items[3] = item;
      c.nodes[3].item = item;
      return item;
    };
    registry.fallback = fallback ? &codec : nullptr;
    EventFactory factory(registry);
    presonus::uc::BasicConnectionState state;
    state.queue = &queue;
    state.factory = &factory;
    state.storage = &storage;
    state.context = &c;
    state.append = [](void *p, EventItem *base) {
      auto &c = *static_cast<Context *>(p);
      auto *item = dynamic_cast<Item *>(base);
      if (!item || c.held)
        std::abort();
      unsigned id = item->id;
      c.trace.push_back(static_cast<unsigned char>(48 + id));
      c.state->lock(c.state->context);
      auto *node = &c.nodes[id];
      if (node->next)
        std::abort();
      if (c.state->head) {
        c.previous[id] = c.nodeID(c.tail);
        c.tail->next = node;
      } else
        c.state->head = node;
      c.tail = node;
      c.state->unlock(c.state->context);
    };
    BasicConnection connection(state);
    bool result = false;
    if (op == 0)
      result = connection.sendEvent(c.source.header);
    else if (op == 1)
      result = connection.queueEvent(itemNull ? nullptr : c.items[2]);
    else
      result = connection.hasQueuedEvents();
    std::array<unsigned, 4> afterOrder{0xffffffffu, 0xffffffffu, 0xffffffffu,
                                       0xffffffffu};
    unsigned count = 0;
    auto *node = storage.head;
    while (node) {
      if (count >= 4)
        return 7;
      afterOrder[count++] = c.nodeID(node);
      node = node->next;
    }
    if (c.nodeID(c.tail) != (count ? afterOrder[count - 1] : 0xffffffffu))
      return 8;
    unsigned live = 0;
    for (unsigned i = 0; i < 4; ++i)
      if (c.items[i])
        live |= 1u << i;
    std::array<std::uint32_t, 19> actual = {live,
                                            c.destroyed[0],
                                            c.destroyed[1],
                                            c.destroyed[2],
                                            c.destroyed[3],
                                            count,
                                            afterOrder[0],
                                            afterOrder[1],
                                            afterOrder[2],
                                            afterOrder[3],
                                            c.nodeID(c.nodes[0].next),
                                            c.nodeID(c.nodes[1].next),
                                            c.nodeID(c.nodes[2].next),
                                            c.nodeID(c.nodes[3].next),
                                            c.previous[0],
                                            c.previous[1],
                                            c.previous[2],
                                            c.previous[3],
                                            c.cloneCalls};
    if (result != bool(expectedResult) || c.invalid || c.held ||
        actual != small || c.trace.size() != traceLength ||
        !std::equal(c.trace.begin(), c.trace.end(), trace.begin())) {
      std::fprintf(stderr, "fixture%u op%u ownership/trace/result mismatch\n",
                   record, op);
      return 9;
    }
    std::array<Image, 5> after{};
    after[0] = save(c.source, c.sourceOriginal);
    for (unsigned i = 0; i < 4; ++i)
      if (c.items[i])
        after[i + 1] = save(c.items[i]->value, c.items[i]->original);
    if (after != expected) {
      unsigned i = 0, off = 0;
      while (i < 5 && after[i] == expected[i])
        ++i;
      while (off < size && after[i][off] == expected[i][off])
        ++off;
      std::fprintf(stderr, "fixture%u item%u byte%u payload mismatch\n", record,
                   i, off);
      return 10;
    }
    c.recording = false;
    for (unsigned i = 0; i < 4; ++i)
      delete c.items[i];
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 11;
  std::printf("%u original ARM BasicConnection fixtures passed with composed "
              "queue/factory and ownership checks\n",
              records);
}
