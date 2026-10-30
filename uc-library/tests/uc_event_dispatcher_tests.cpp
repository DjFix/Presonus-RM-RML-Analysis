#include "presonus/uc/event_dispatcher.hpp"
#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace Presonus::UC;
using namespace presonus::uc;
constexpr unsigned none = 0xffffffffu;
using Body = std::array<unsigned char, 152>;
using Row = std::array<unsigned, 8>;
static void require(bool value) {
  if (!value)
    throw std::runtime_error("dispatcher fixture mismatch");
}
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static int signedBits(unsigned bits) {
  int n;
  std::memcpy(&n, &bits, 4);
  return n;
}
static void put(Body &body, unsigned offset, unsigned value, unsigned n = 4) {
  for (unsigned i = 0; i < n; ++i)
    body[offset + i] = static_cast<unsigned char>(value >> (8 * i));
}
static ParamValueEvent decode(const Body &b) {
  ParamValueEvent event;
  event.header = {word(b.data()), word(b.data() + 4), word(b.data() + 8),
                  word(b.data() + 12)};
  std::memcpy(event.path.data(), b.data() + 16, 128);
  event.index = static_cast<unsigned short>(b[144] | (unsigned(b[145]) << 8));
  std::memcpy(event.reserved92.data(), b.data() + 146, 2);
  event.valueBits = word(b.data() + 148);
  return event;
}
static Body snapshot(const ParamValueEvent &v) {
  Body b{};
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
static unsigned readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  require(bool(f));
  return word(b.data());
}
static std::vector<unsigned> readSequence(std::ifstream &f) {
  std::vector<unsigned> out(readWord(f));
  for (auto &v : out)
    v = readWord(f);
  return out;
}
static Body readBody(std::ifstream &f) {
  Body b{};
  f.read(reinterpret_cast<char *>(b.data()), b.size());
  require(bool(f));
  return b;
}
struct Context;
struct Item : EventItem {
  Context &context;
  unsigned id;
  ParamValueEvent value;
  Item(Context &c, unsigned i, const Body &body)
      : context(c), id(i), value(decode(body)) {}
  Event &getData() override;
  ~Item() override;
};
struct Handler : IEventHandler {
  Context &context;
  unsigned id;
  Handler(Context &c, unsigned i) : context(c), id(i) {}
  int handleEvent(void *, const Event &) override;
};
struct Context {
  EventDispatcherState state;
  EventDispatcher dispatcher{state};
  std::array<Item *, 4> items{};
  std::array<Handler, 3> handlers{
      {Handler(*this, 0), Handler(*this, 1), Handler(*this, 2)}};
  std::array<Body, 4> frozen{};
  std::array<int, 3> results{};
  ParamValueEvent source;
  unsigned key = 0, getmask = 0, mutate = 0, deleteMask = 0, deleted = 0,
           held = 0;
  bool recording = true;
  std::vector<Row> trace;
  Context() {
    state.auditContext = this;
    state.audit = [](void *p, DispatcherAudit stage) {
      auto &c = *static_cast<Context *>(p);
      unsigned n = unsigned(stage), bit = n <= 2 ? 1 : 2;
      if (n == 1 || n == 3) {
        require(!(c.held & bit));
        c.held |= bit;
      } else
        require(c.held & bit);
      auto q = c.order();
      c.row({n, 0, 0, q.empty() ? none : q.front(), q.empty() ? none : q.back(),
             unsigned(q.size()), c.held, c.deleted});
      if (n == 2 || n == 4)
        c.held &= ~bit;
    };
    state.typedContext = this;
    state.typedValue = [](void *p, const Event &e,
                          QueueValueKind kind) -> void * {
      auto &c = *static_cast<Context *>(p);
      require(kind == QueueValueKind::Value);
      if (&e == &c.source.header)
        return &c.source;
      for (auto *i : c.items)
        if (i && &i->value.header == &e)
          return &i->value;
      throw std::runtime_error("unknown typed payload");
    };
  }
  void row(std::initializer_list<unsigned> values) {
    Row r{};
    std::copy(values.begin(), values.end(), r.begin());
    trace.push_back(r);
  }
  unsigned idFor(EventItem *item) const {
    for (unsigned i = 0; i < items.size(); ++i)
      if (items[i] == item)
        return i;
    throw std::runtime_error("unknown live item");
  }
  std::vector<unsigned> order() const {
    std::vector<unsigned> q;
    Core::ListIterator<EventItem *> iterator(state.queued);
    while (!iterator.done())
      q.push_back(idFor(iterator.next()));
    return q;
  }
  ~Context() {
    recording = false;
    state.queued.removeAll();
    for (auto *i : items)
      delete i;
  }
};
Event &Item::getData() {
  require(!(context.deleted & (1u << id)));
  if (context.getmask & (1u << id))
    value.header.routeB = context.key;
  context.row({5, id, value.header.routeB, value.header.routeA, 0, 0,
               context.held, context.deleted});
  return value.header;
}
Item::~Item() {
  if (context.recording) {
    require(!(context.deleted & (1u << id)));
    context.row({7, id, value.valueBits, value.index, value.header.routeA,
                 value.header.routeB, context.held, context.deleted});
    context.frozen[id] = snapshot(value);
    context.deleted |= 1u << id;
  }
  context.items[id] = nullptr;
}
int Handler::handleEvent(void *raw, const Event &event) {
  auto *item = static_cast<EventItem *>(raw);
  unsigned ident = context.idFor(item);
  require(context.held == 1);
  const int result = context.results[id];
  context.row({6, id, ident, event.type, event.routeB, unsigned(result),
               context.held, context.deleted});
  if (context.mutate & (1u << id)) {
    auto &value = const_cast<Event &>(event);
    value.reserved04 ^= 0x13579bdf;
    value.routeA += 1;
  }
  if (result == 1 && (context.deleteMask & (1u << id)))
    delete item;
  return result;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  char magic[8];
  f.read(magic, 8);
  require(!std::memcmp(magic, "UCDPv001", 8));
  unsigned count = readWord(f);
  for (unsigned row = 0; row < count; ++row) {
    std::array<unsigned, 12> meta{};
    for (auto &v : meta)
      v = readWord(f);
    Context c;
    unsigned role = meta[0], op = meta[1], arg = meta[4];
    c.key = meta[2];
    c.getmask = meta[5];
    c.mutate = meta[6];
    c.deleteMask = meta[7];
    for (unsigned i = 0; i < 3; ++i)
      c.results[i] = signedBits(meta[9 + i]);
    c.state.fallback = meta[8] == none ? nullptr : &c.handlers.at(meta[8]);
    auto initialQueue = readSequence(f), external = readSequence(f);
    for (unsigned id : external)
      require(c.state.externalIDs.add(signedBits(id)));
    unsigned registrations = readWord(f);
    for (unsigned i = 0; i < registrations; ++i) {
      unsigned key = readWord(f), id = readWord(f);
      c.state.handlers.add(signedBits(key),
                           id == none ? nullptr : &c.handlers.at(id));
    }
    for (unsigned i = 0; i < 4; ++i)
      c.items[i] = new Item(c, i, readBody(f));
    c.source = decode(readBody(f));
    for (unsigned id : initialQueue)
      c.state.queued.append(c.items.at(id));
    unsigned expectedResult = readWord(f), expectedDeleted = readWord(f);
    auto expectedQueue = readSequence(f);
    std::array<Body, 4> bodies;
    for (auto &b : bodies)
      b = readBody(f);
    Body source = readBody(f);
    unsigned n = readWord(f);
    std::vector<Row> expectedTrace(n);
    for (auto &r : expectedTrace)
      for (auto &v : r)
        v = readWord(f);
    unsigned result = 0;
    switch (op) {
    case 0: {
      int key = signedBits(c.key);
      result =
          unsigned(EventDispatcher::hashHandlerKey(key, signedBits(meta[3])));
      break;
    }
    case 1:
      result = c.dispatcher.updateEvent(c.source.header);
      break;
    case 2:
      result = c.dispatcher.hasEvents();
      break;
    case 3:
      result = c.dispatcher.isExternalHandler(signedBits(c.key));
      break;
    case 4:
      c.dispatcher.queueEvent(arg == none ? nullptr : c.items.at(arg));
      break;
    case 5:
      c.dispatcher.dispatchOne(c.items.at(arg));
      break;
    case 6:
      c.dispatcher.dispatchAll();
      break;
    default:
      return 3;
    }
    bool ok = result == expectedResult && c.deleted == expectedDeleted &&
              c.order() == expectedQueue && c.trace == expectedTrace &&
              !c.held && snapshot(c.source) == source;
    for (unsigned i = 0; i < 4; ++i)
      ok = ok && (c.items[i] ? snapshot(c.items[i]->value) : c.frozen[i]) ==
                     bodies[i];
    if (!ok) {
      std::cerr << "dispatcher mismatch row=" << row << " role=" << role
                << " op=" << op << " result=" << result << '/' << expectedResult
                << " deleted=" << c.deleted << '/' << expectedDeleted
                << " trace=" << c.trace.size() << '/' << expectedTrace.size()
                << '\n';
      for (unsigned i = 0; i < std::min(c.trace.size(), expectedTrace.size());
           ++i)
        if (c.trace[i] != expectedTrace[i]) {
          std::cerr << "first trace mismatch=" << i << '\n';
          for (auto v : c.trace[i])
            std::cerr << std::hex << v << ' ';
          std::cerr << '\n';
          for (auto v : expectedTrace[i])
            std::cerr << std::hex << v << ' ';
          std::cerr << '\n';
          break;
        }
      return 1;
    }
  }
  require(f.peek() == std::char_traits<char>::eof());
  std::cout << count
            << " original ARM dispatcher cases passed with actual CCL "
               "map/vector/list/locks and sealed coalescer\n";
}
