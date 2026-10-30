#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <sstream>
#include <vector>
using namespace Presonus::UC;
namespace {
bool tracking = false;
unsigned factoryDepth = 0, nextID = 1, clones = 0, failAt = 0;
std::ostringstream trace;
struct Item final : EventItem {
  Core::IO::Buffer buffer;
  MessageEvent message;
  MessageChunkEvent chunk;
  unsigned id = nextID++;
  int flags = 0;
  bool isChunk = false;
  Event &getData() override { return isChunk ? chunk.header : message.header; }
  ~Item() override {
    if (tracking)
      trace << "X " << id << ';';
  }
};
void dump(std::ostream &out, const Event &event) {
  out << event.type << ' ' << event.reserved04 << ' ' << event.routeA << ' '
      << event.routeB;
  const void *data;
  unsigned size;
  if (event.type == 0x434b) {
    const auto &e = *reinterpret_cast<const MessageChunkEvent *>(&event);
    size = e.sizeBits;
    data = e.data;
    out << ' ' << size << ' ' << e.word24 << ' ' << e.word28 << ' ' << e.word32;
  } else {
    const auto &e = *reinterpret_cast<const MessageEvent *>(&event);
    size = e.sizeBits;
    data = e.data;
    out << ' ' << size;
  }
  out << ' ';
  if (size == 0)
    out << '-';
  if (size > 40000)
    throw std::runtime_error("payload fixture bound");
  constexpr char digits[] = "0123456789abcdef";
  const auto *bytes = static_cast<const unsigned char *>(data);
  for (unsigned n = 0; n < size; ++n)
    out << digits[bytes[n] >> 4] << digits[bytes[n] & 15];
}
struct Provider {
  presonus::uc::CclFactoryRegistry registry;
  EventFactory factory{registry.registry()};
  presonus::uc::FactoryCodec codec;
  unsigned rejects = 0;
  Provider(unsigned tag) {
    codec.context = this;
    codec.create = [](void *) -> EventItem * {
      auto *p = new Item;
      p->message.header = {0x4a4d, 24, 0, 0};
      return p;
    };
    codec.clone = [](void *, const Event &event) -> EventItem * {
      if (++clones == failAt)
        return nullptr;
      auto *p = new Item;
      p->isChunk = event.type == 0x434b;
      const void *data;
      unsigned size;
      if (p->isChunk) {
        p->chunk = *reinterpret_cast<const MessageChunkEvent *>(&event);
        data = p->chunk.data;
        size = p->chunk.sizeBits;
      } else {
        p->message = *reinterpret_cast<const MessageEvent *>(&event);
        data = p->message.data;
        size = p->message.sizeBits;
      }
      if (size > 40000 || !p->buffer.resize(size)) {
        delete p;
        throw std::runtime_error("codec buffer bound");
      }
      if (size)
        p->buffer.copyFrom(data, size);
      if (p->isChunk)
        p->chunk.data = p->buffer.getAddress();
      else
        p->message.data = p->buffer.getAddress();
      return p;
    };
    codec.write = [](void *, BufferWriter &w, const Event &e) {
      return EventClass{}.write(w, e);
    };
    codec.read = [](void *, EventItem *i, BufferReader &r) {
      return i && EventClass{}.read(i->getData(), r);
    };
    codec.destroy = [](void *, EventItem *i) { delete i; };
    registry.registry().append(static_cast<int>(tag), &codec);
    if (tag != 0x434b)
      registry.registry().append(0x434b, &codec);
    if (tag != 0x4a4d)
      registry.registry().append(0x4a4d, &codec);
  }
  void bind(presonus::uc::NetworkManagerState &s) {
    s.context = this;
    s.messageView = [](void *, const Event &e) -> const MessageEvent & {
      return *reinterpret_cast<const MessageEvent *>(&e);
    };
    s.messageItemView = [](void *, EventItem &i) -> MessageEvent & {
      return static_cast<Item &>(i).message;
    };
    s.chunkView = [](void *, const Event &e) -> const MessageChunkEvent & {
      return *reinterpret_cast<const MessageChunkEvent *>(&e);
    };
    s.storage = [](void *, EventItem &i) -> Core::IO::Buffer & {
      return static_cast<Item &>(i).buffer;
    };
    s.storeFlags = [](void *, EventItem &i, int flags) {
      static_cast<Item &>(i).flags = flags;
    };
    s.reportOversized = [](void *p) { ++static_cast<Provider *>(p)->rejects; };
  }
};
struct Handler final : IEventHandler {
  unsigned id = 0;
  int result = 0;
  int handleEvent(void *context, const Event &e) override {
    if (tracking)
      trace << "H " << id << ' ' << bool(context) << ' ' << e.type << ' '
            << e.reserved04 << ' ' << e.routeA << ' ' << e.routeB << ' '
            << result << ';';
    return result;
  }
};
int signedBits(unsigned bits) {
  int v;
  std::memcpy(&v, &bits, 4);
  return v;
}
} // namespace
extern "C" bool
__real__ZN8Presonus2UC15EventDispatcher11updateEventERKNS0_5EventE(
    EventDispatcher *, const Event &);
extern "C" bool
__wrap__ZN8Presonus2UC15EventDispatcher11updateEventERKNS0_5EventE(
    EventDispatcher *p, const Event &e) {
  bool r =
      __real__ZN8Presonus2UC15EventDispatcher11updateEventERKNS0_5EventE(p, e);
  if (tracking)
    trace << "U " << r << ';';
  return r;
}
extern "C" void
__real__ZN8Presonus2UC15EventDispatcher10queueEventEPNS0_9EventItemE(
    EventDispatcher *, EventItem *);
extern "C" void
__wrap__ZN8Presonus2UC15EventDispatcher10queueEventEPNS0_9EventItemE(
    EventDispatcher *p, EventItem *e) {
  if (tracking) {
    auto *i = static_cast<Item *>(e);
    trace << "Q " << i->id << ' ' << i->flags << ' ';
    dump(trace, i->getData());
    trace << ';';
  }
  __real__ZN8Presonus2UC15EventDispatcher10queueEventEPNS0_9EventItemE(p, e);
}
extern "C" void
__real__ZN8Presonus2UC15EventDispatcher11dispatchOneEPNS0_9EventItemE(
    EventDispatcher *, EventItem *);
extern "C" void
__wrap__ZN8Presonus2UC15EventDispatcher11dispatchOneEPNS0_9EventItemE(
    EventDispatcher *p, EventItem *e) {
  if (tracking) {
    trace << "D " << static_cast<Item *>(e)->id << ' ';
    dump(trace, e->getData());
    trace << ';';
  }
  __real__ZN8Presonus2UC15EventDispatcher11dispatchOneEPNS0_9EventItemE(p, e);
}
extern "C" int
__real__ZN8Presonus2UC15EventDispatcher10addHandlerEPNS0_13IEventHandlerEi(
    EventDispatcher *, IEventHandler *, int);
extern "C" int
__wrap__ZN8Presonus2UC15EventDispatcher10addHandlerEPNS0_13IEventHandlerEi(
    EventDispatcher *p, IEventHandler *h, int f) {
  int id =
      __real__ZN8Presonus2UC15EventDispatcher10addHandlerEPNS0_13IEventHandlerEi(
          p, h, f);
  if (tracking)
    trace << "A " << bool(h) << ' ' << f << ' ' << id << ';';
  return id;
}
extern "C" bool
__real__ZN8Presonus2UC15EventDispatcher13removeHandlerEPNS0_13IEventHandlerE(
    EventDispatcher *, IEventHandler *);
extern "C" bool
__wrap__ZN8Presonus2UC15EventDispatcher13removeHandlerEPNS0_13IEventHandlerE(
    EventDispatcher *p, IEventHandler *h) {
  bool r =
      __real__ZN8Presonus2UC15EventDispatcher13removeHandlerEPNS0_13IEventHandlerE(
          p, h);
  if (tracking)
    trace << "R " << bool(h) << ' ' << r << ';';
  return r;
}
extern "C" EventItem *
__real__ZN8Presonus2UC12EventFactory6createERKNS0_5EventE(EventFactory *,
                                                          const Event &);
extern "C" EventItem *
__wrap__ZN8Presonus2UC12EventFactory6createERKNS0_5EventE(EventFactory *p,
                                                          const Event &e) {
  if (tracking) {
    trace << "C ";
    dump(trace, e);
    trace << ';';
  }
  ++factoryDepth;
  auto *r = __real__ZN8Presonus2UC12EventFactory6createERKNS0_5EventE(p, e);
  --factoryDepth;
  if (tracking && !r)
    trace << "N;";
  return r;
}
extern "C" EventItem *
__real__ZN8Presonus2UC12EventFactory10createTypeEi(EventFactory *, int);
extern "C" EventItem *
__wrap__ZN8Presonus2UC12EventFactory10createTypeEi(EventFactory *p, int type) {
  if (tracking)
    trace << "Y " << type << ';';
  ++factoryDepth;
  auto *r = __real__ZN8Presonus2UC12EventFactory10createTypeEi(p, type);
  --factoryDepth;
  return r;
}
extern "C" bool __real__ZN4Core2IO6Buffer6resizeEj(Core::IO::Buffer *,
                                                   unsigned);
extern "C" bool __wrap__ZN4Core2IO6Buffer6resizeEj(Core::IO::Buffer *p,
                                                   unsigned n) {
  if (tracking && !factoryDepth)
    trace << "B " << n << ';';
  return __real__ZN4Core2IO6Buffer6resizeEj(p, n);
}
extern "C" unsigned __real__ZN4Core2IO6Buffer8copyFromEjPKvj(Core::IO::Buffer *,
                                                             unsigned,
                                                             const void *,
                                                             unsigned);
extern "C" unsigned
__wrap__ZN4Core2IO6Buffer8copyFromEjPKvj(Core::IO::Buffer *p, unsigned o,
                                         const void *d, unsigned n) {
  if (tracking && !factoryDepth)
    trace << "P " << o << ' ' << n << ';';
  return __real__ZN4Core2IO6Buffer8copyFromEjPKvj(p, o, d, n);
}
int main() {
  try {
    unsigned op, tag, reserved, ra, rb, total, flags, seed, fail, count,
        context, pattern;
    std::array<int, 4> responses;
    while (std::cin >> op >> tag >> reserved >> ra >> rb >> total >> flags >>
           seed >> fail >> count >> context >> pattern >> responses[0] >>
           responses[1] >> responses[2] >> responses[3]) {
      if (op > 4 || count > 4 || context > 1 || pattern > 3)
        throw std::runtime_error("fixture bound");
      tracking = false;
      trace.str("");
      trace.clear();
      nextID = 1;
      clones = 0;
      failAt = fail;
      Provider provider(tag);
      presonus::uc::EventDispatcherState ds;
      EventDispatcher dispatcher(ds);
      presonus::uc::NetworkManagerState state{dispatcher, provider.factory};
      provider.bind(state);
      FixtureManager network(state);
      std::array<Handler, 5> handlers;
      for (unsigned n = 0; n < 5; ++n) {
        handlers[n].id = n + 1;
        handlers[n].result = n < 4 ? responses[n] : 0;
      }
      for (unsigned n = 0; n < count; ++n)
        state.handlers.add(&handlers[n]);
      if (op == 4) {
        int id = -1;
        network.registerHandler(id, &handlers[4]);
        if (id != 100 || rb != 100 || total > 40000)
          throw std::runtime_error("chunk fixture bound");
      }
      std::vector<unsigned char> bytes(total <= 40000 ? total : 0);
      for (unsigned n = 0; n < bytes.size(); ++n)
        bytes[n] = static_cast<unsigned char>(seed + n * 73);
      MessageEvent event{{tag, reserved, ra, rb}, bytes.data(), total};
      Item *incoming = nullptr;
      if (op == 4) {
        std::vector<unsigned> offsets;
        for (unsigned n = 0; n + 0x3f80 < total; n += 0x3f80)
          offsets.push_back(n);
        auto seedItem = [&](unsigned offset, unsigned length, unsigned a) {
          auto *item = new Item;
          item->isChunk = true;
          item->chunk = {{0x434b, 36, a, rb},
                         bytes.data() + offset,
                         length,
                         tag,
                         offset,
                         total};
          if (!item->buffer.resize(length))
            throw std::bad_alloc();
          if (length)
            item->buffer.copyFrom(bytes.data() + offset, length);
          item->chunk.data = item->buffer.getAddress();
          return item;
        };
        if ((pattern & 1) && !offsets.empty())
          state.pendingChunks.append(seedItem(0, 0x3f80, ra ^ 1));
        for (unsigned offset : offsets)
          state.pendingChunks.append(seedItem(offset, 0x3f80, ra));
        if ((pattern & 2) && !offsets.empty())
          state.pendingChunks.append(seedItem(0, 0x3f80, ra));
        const unsigned offset = offsets.empty() ? 0 : offsets.back() + 0x3f80;
        incoming = seedItem(offset, total - offset, ra);
      }
      tracking = true;
      int result = 0, id = -1;
      if (op == 0)
        result = network.sendEvent(event.header, signedBits(flags));
      else if (op == 1)
        result = network.sendChunks(event);
      else if (op == 2)
        result =
            network.handleEvent(context ? &provider : nullptr, event.header);
      else if (op == 3) {
        result = network.registerHandler(id, context ? &handlers[0] : nullptr);
        result += network.unregisterHandler(context ? &handlers[0] : nullptr);
        result += network.unregisterHandler(context ? &handlers[0] : nullptr);
      } else
        result = network.handleEvent(incoming, incoming->chunk.header);
      tracking = false;
      std::cout << result << '|' << id << '|' << provider.rejects << '|'
                << trace.str() << '|' << ds.queued.count();
      for (Core::ListIterator<EventItem *> i(ds.queued); !i.done();) {
        auto *p = static_cast<Item *>(i.next());
        std::cout << ' ' << p->id << ' ' << p->flags << ' ';
        dump(std::cout, p->getData());
      }
      std::cout << '|' << state.pendingChunks.count();
      for (Core::ListIterator<EventItem *> i(state.pendingChunks); !i.done();) {
        auto *p = static_cast<Item *>(i.next());
        std::cout << ' ' << p->id << ' ';
        dump(std::cout, p->getData());
      }
      std::cout << '\n';
      if (incoming && result != 1)
        delete incoming;
      while (!state.pendingChunks.isEmpty())
        delete state.pendingChunks.removeFirst();
      while (auto *p = ds.retrieve())
        delete p;
    }
    if (!std::cin.eof())
      throw std::runtime_error("invalid input");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
