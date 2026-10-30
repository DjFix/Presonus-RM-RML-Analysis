#include "presonus/uc/event_queue.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <type_traits>
#include <variant>
#include <vector>
using namespace Presonus::UC;
constexpr unsigned imageSize = 1216;
using Image = std::array<unsigned char, imageSize>;
using Payload =
    std::variant<ParamValueEvent, ParamIncrementEvent, ParamColorEvent,
                 ParamStringEvent, ParamStringListEvent, ParamRangeEvent,
                 FileDataRateEvent, TimeCodeEvent>;
static std::uint32_t word(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static unsigned short half(const unsigned char *p) {
  return static_cast<unsigned short>(p[0] | (unsigned(p[1]) << 8));
}
static void put(Image &b, unsigned off, std::uint32_t v, unsigned n = 4) {
  for (unsigned i = 0; i < n; ++i)
    b[off + i] = static_cast<unsigned char>(v >> (8 * i));
}
template <class T> void load(T &v, const Image &b) {
  v.header = {word(b.data()), word(b.data() + 4), word(b.data() + 8),
              word(b.data() + 12)};
  if constexpr (std::is_same_v<T, FileDataRateEvent>) {
    v.idBits = word(b.data() + 16);
    for (unsigned i = 0; i < 3; ++i)
      v.wordBits[i] = word(b.data() + 20 + 4 * i);
  } else if constexpr (std::is_same_v<T, TimeCodeEvent>) {
    v.keyBits = word(b.data() + 16);
    v.recordCount = b[20];
    std::memcpy(v.reserved15.data(), b.data() + 21, 3);
    for (unsigned i = 0; i < 4; ++i) {
      v.records[i].a = b[24 + 16 * i];
      v.records[i].b = b[25 + 16 * i];
      std::memcpy(v.records[i].reserved.data(), b.data() + 26 + 16 * i, 6);
      std::memcpy(v.records[i].rawBytes.data(), b.data() + 32 + 16 * i, 8);
    }
  } else {
    std::memcpy(v.path.data(), b.data() + 16, 128);
    v.index = half(b.data() + 144);
    if constexpr (std::is_same_v<T, ParamValueEvent>) {
      std::memcpy(v.reserved92.data(), b.data() + 146, 2);
      v.valueBits = word(b.data() + 148);
    } else if constexpr (std::is_same_v<T, ParamIncrementEvent>)
      v.incrementBits = half(b.data() + 146);
    else if constexpr (std::is_same_v<T, ParamStringEvent>)
      std::memcpy(v.text.data(), b.data() + 146, 256);
    else {
      std::memcpy(v.reserved92.data(), b.data() + 146, 2);
      if constexpr (std::is_same_v<T, ParamColorEvent>)
        v.colorBits = word(b.data() + 148);
      else if constexpr (std::is_same_v<T, ParamStringListEvent>) {
        v.listFieldBits = word(b.data() + 148);
        std::memcpy(v.text.data(), b.data() + 152, 1024);
      } else {
        for (unsigned i = 0; i < 5; ++i)
          v.wordBits[i] = word(b.data() + 148 + 4 * i);
        for (unsigned i = 0; i < 2; ++i)
          std::memcpy(v.labels[i].data(), b.data() + 168 + 32 * i, 32);
      }
    }
  }
}
template <class T> void save(const T &v, Image &b) {
  put(b, 0, v.header.type);
  put(b, 4, v.header.reserved04);
  put(b, 8, v.header.routeA);
  put(b, 12, v.header.routeB);
  if constexpr (std::is_same_v<T, FileDataRateEvent>) {
    put(b, 16, v.idBits);
    for (unsigned i = 0; i < 3; ++i)
      put(b, 20 + 4 * i, v.wordBits[i]);
  } else if constexpr (std::is_same_v<T, TimeCodeEvent>) {
    put(b, 16, v.keyBits);
    b[20] = v.recordCount;
    std::memcpy(b.data() + 21, v.reserved15.data(), 3);
    for (unsigned i = 0; i < 4; ++i) {
      b[24 + 16 * i] = v.records[i].a;
      b[25 + 16 * i] = v.records[i].b;
      std::memcpy(b.data() + 26 + 16 * i, v.records[i].reserved.data(), 6);
      std::memcpy(b.data() + 32 + 16 * i, v.records[i].rawBytes.data(), 8);
    }
  } else {
    std::memcpy(b.data() + 16, v.path.data(), 128);
    put(b, 144, v.index, 2);
    if constexpr (std::is_same_v<T, ParamValueEvent>) {
      std::memcpy(b.data() + 146, v.reserved92.data(), 2);
      put(b, 148, v.valueBits);
    } else if constexpr (std::is_same_v<T, ParamIncrementEvent>)
      put(b, 146, v.incrementBits, 2);
    else if constexpr (std::is_same_v<T, ParamStringEvent>)
      std::memcpy(b.data() + 146, v.text.data(), 256);
    else {
      std::memcpy(b.data() + 146, v.reserved92.data(), 2);
      if constexpr (std::is_same_v<T, ParamColorEvent>)
        put(b, 148, v.colorBits);
      else if constexpr (std::is_same_v<T, ParamStringListEvent>) {
        put(b, 148, v.listFieldBits);
        std::memcpy(b.data() + 152, v.text.data(), 1024);
      } else {
        for (unsigned i = 0; i < 5; ++i)
          put(b, 148 + 4 * i, v.wordBits[i]);
        for (unsigned i = 0; i < 2; ++i)
          std::memcpy(b.data() + 168 + 32 * i, v.labels[i].data(), 32);
      }
    }
  }
}
struct Context;
struct Item : EventItem {
  Payload value;
  Image original{};
  unsigned id = 0;
  Context *context = nullptr;
  bool throwOnRead = false;
  static unsigned destructions;
  ~Item() override { ++destructions; }
  Event &data() {
    return std::visit([](auto &v) -> Event & { return v.header; }, value);
  }
  Event &getData() override;
  void initialize(unsigned kind, const Image &b) {
    original = b;
    switch (kind) {
    case 0:
      value = ParamValueEvent{};
      break;
    case 1:
      value = ParamIncrementEvent{};
      break;
    case 2:
      value = ParamColorEvent{};
      break;
    case 3:
      value = ParamStringEvent{};
      break;
    case 4:
      value = ParamStringListEvent{};
      break;
    case 5:
      value = ParamRangeEvent{};
      break;
    case 6:
      value = FileDataRateEvent{};
      break;
    case 7:
      value = TimeCodeEvent{};
      break;
    default:
      std::abort();
    }
    std::visit([&](auto &v) { load(v, b); }, value);
  }
  Image snapshot() const {
    Image b = original;
    std::visit([&](const auto &v) { save(v, b); }, value);
    return b;
  }
};
unsigned Item::destructions = 0;
struct Context {
  bool held = false, invalid = false;
  std::vector<unsigned char> trace;
  std::array<Item, 5> *items = nullptr;
  std::array<Image, 5> atUnlock{};
};
Event &Item::getData() {
  if (!context->held)
    context->invalid = true;
  context->trace.push_back(static_cast<unsigned char>(16 + id));
  if (throwOnRead)
    throw std::runtime_error("portable callback unwind test");
  return data();
}
static presonus::uc::EventQueueState stateFor(Context &c) {
  presonus::uc::EventQueueState state;
  state.context = &c;
  state.lock = [](void *p) {
    auto &c = *static_cast<Context *>(p);
    if (c.held)
      c.invalid = true;
    c.held = true;
    c.trace.push_back(1);
  };
  state.unlock = [](void *p) {
    auto &c = *static_cast<Context *>(p);
    if (!c.held)
      c.invalid = true;
    for (unsigned i = 0; i < 5; ++i)
      c.atUnlock[i] = (*c.items)[i].snapshot();
    c.trace.push_back(2);
    c.held = false;
  };
  state.value = [](void *p, const Event &event,
                   presonus::uc::QueueValueKind kind) -> void * {
    auto &c = *static_cast<Context *>(p);
    if (!c.held)
      c.invalid = true;
    for (auto &i : *c.items)
      if (&i.data() == &event) {
        if (i.value.index() != static_cast<unsigned>(kind))
          std::abort();
        return std::visit([](auto &v) -> void * { return &v; }, i.value);
      }
    std::abort();
  };
  return state;
}
static bool invoke(EventQueue &q, unsigned kind, bool dispatch,
                   const Event &e) {
  if (dispatch)
    return q.updateEvent(e);
  switch (kind) {
  case 0:
    return q.update<ParamValueEvent>(e);
  case 1:
    return q.update<ParamIncrementEvent>(e);
  case 2:
    return q.update<ParamColorEvent>(e);
  case 3:
    return q.update<ParamStringEvent>(e);
  case 4:
    return q.update<ParamStringListEvent>(e);
  case 5:
    return q.update<ParamRangeEvent>(e);
  case 6:
    return q.update<FileDataRateEvent>(e);
  case 7:
    return q.update<TimeCodeEvent>(e);
  default:
    std::abort();
  }
}
static std::uint32_t readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  if (!f)
    std::abort();
  return word(b.data());
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 8> magic{};
  f.read(reinterpret_cast<char *>(magic.data()), 8);
  if (std::memcmp(magic.data(), "UCQUv001", 8))
    return 3;
  unsigned records = readWord(f);
  for (unsigned record = 0; record < records; ++record) {
    unsigned kind = readWord(f), dispatch = readWord(f), n = readWord(f),
             orderBits = readWord(f), expectedResult = readWord(f),
             traceLength = readWord(f);
    if (kind > 7 || n > 4 || traceLength > 16)
      return 4;
    std::array<unsigned char, 16> trace{};
    f.read(reinterpret_cast<char *>(trace.data()), 16);
    std::array<Image, 5> before{};
    for (auto &b : before)
      f.read(reinterpret_cast<char *>(b.data()), b.size());
    if (!f)
      return 5;
    auto expected = before;
    unsigned runs = readWord(f), lastEnd = 0;
    for (unsigned i = 0; i < runs; ++i) {
      unsigned start = readWord(f), length = readWord(f);
      if (start < lastEnd || start + length > 5 * imageSize)
        return 6;
      for (unsigned j = 0; j < length; ++j) {
        char ch;
        f.get(ch);
        expected[(start + j) / imageSize][(start + j) % imageSize] =
            static_cast<unsigned char>(ch);
      }
      lastEnd = start + length;
    }
    Context c;
    std::array<Item, 5> items;
    c.items = &items;
    for (unsigned i = 0; i < 5; ++i) {
      items[i].initialize(kind, before[i]);
      items[i].id = i ? i - 1 : 99;
      items[i].context = &c;
    }
    std::array<presonus::uc::EventQueueNode, 4> nodes{};
    std::array<unsigned, 4> order{};
    for (unsigned i = 0; i < 4; ++i) {
      order[i] = (orderBits >> (2 * i)) & 3;
      nodes[i].item = &items[i + 1];
    }
    for (unsigned i = 0; i < n; ++i)
      nodes[order[i]].next = i + 1 < n ? &nodes[order[i + 1]] : nullptr;
    auto state = stateFor(c);
    state.head = n ? &nodes[order[0]] : nullptr;
    const auto originalNodes = nodes;
    auto *head = state.head;
    EventQueue q(state);
    unsigned destructions = Item::destructions;
    bool result = invoke(q, kind, dispatch, items[0].data());
    if (result != bool(expectedResult) || c.invalid || c.held ||
        state.head != head || Item::destructions != destructions ||
        c.trace.size() != traceLength ||
        !std::equal(c.trace.begin(), c.trace.end(), trace.begin())) {
      std::fprintf(stderr, "fixture%u result/trace/ownership mismatch\n",
                   record);
      return 7;
    }
    for (unsigned i = 0; i < 4; ++i)
      if (nodes[i].item != originalNodes[i].item ||
          nodes[i].next != originalNodes[i].next)
        return 8;
    for (unsigned i = 0; i < 5; ++i) {
      auto actual = items[i].snapshot();
      if (actual != expected[i] ||
          (traceLength && c.atUnlock[i] != expected[i])) {
        unsigned off = 0;
        while (off < imageSize && actual[off] == expected[i][off])
          ++off;
        std::fprintf(
            stderr, "fixture%u kind%u item%u byte%u mutation/unlock mismatch\n",
            record, kind, i, off);
        return 9;
      }
    }
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 10;
  // Native-only RAII exception behavior. This is not an ARM unwind proof.
  {
    Context c;
    std::array<Item, 5> items;
    c.items = &items;
    for (unsigned i = 0; i < 5; ++i) {
      Image b{};
      items[i].initialize(0, b);
      items[i].context = &c;
      items[i].id = i ? i - 1 : 99;
    }
    items[1].throwOnRead = true;
    presonus::uc::EventQueueNode node{&items[1], nullptr};
    auto state = stateFor(c);
    state.head = &node;
    EventQueue q(state);
    bool caught = false;
    try {
      q.update<ParamValueEvent>(items[0].data());
    } catch (const std::runtime_error &) {
      caught = true;
    }
    if (!caught || c.held || c.invalid ||
        c.trace != std::vector<unsigned char>({1, 16, 2}))
      return 11;
  }
  std::printf("%u original ARM EventQueue fixtures passed\n1 portable RAII "
              "exception cleanup check passed (ARM unwind unverified)\n",
              records);
}
