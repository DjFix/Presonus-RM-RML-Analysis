#include "connection_fixture.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/connection_receive.hpp"
#include "presonus/uc/socket_channel.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
using namespace Presonus::UC;
constexpr unsigned none = 0xffffffffu, noOverride = 0x7fffffffu,
                   bufferSize = 16390;
using Body = std::array<unsigned char, 152>;
using Row = std::array<std::uint32_t, 8>;
static std::uint32_t word(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static unsigned readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  if (!f)
    std::abort();
  return word(b.data());
}
static int signedBits(unsigned v) {
  int x;
  static_assert(sizeof(x) == 4);
  std::memcpy(&x, &v, 4);
  return x;
}
static void put(Body &b, unsigned off, std::uint32_t v, unsigned n = 4) {
  for (unsigned i = 0; i < n; ++i)
    b[off + i] = static_cast<unsigned char>(v >> (8 * i));
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
static void require(bool b) {
  if (!b)
    std::abort();
}
struct Context;
struct Item : presonus::uc::TypedEventItem<ParamValueEvent> {
  Context *context;
  unsigned id;
  Item(Context *c, unsigned i) : context(c), id(i) {
    value = {};
    value.header.type = 20566;
  }
  ~Item() override;
  Event &getData() override;
};
struct Response {
  int result;
  std::vector<unsigned char> data;
};
struct Context {
  presonus::uc::ConnectionReceiveState state;
  Core::IO::Buffer buffer{bufferSize};
  Core::Threads::Lock actualObserverLock;
  std::vector<unsigned> ready, available;
  std::vector<Response> responses;
  unsigned readyCursor = 0, availableCursor = 0, readCursor = 0, created = 0,
           allocCalls = 0;
  unsigned lockOverride = noOverride;
  bool allocNull = false, observerHeld = false, queueHeld = false,
       recording = true, invalid = false;
  std::array<Item *, 4> items{};
  std::array<Body, 4> frozen{};
  std::array<unsigned, 4> destroyed{}, next{none, none, none, none},
      previous{none, none, none, none};
  std::vector<unsigned> queue;
  std::vector<Row> trace;
  EventFactory *factory = nullptr;
  presonus::uc::ParamValueFactoryCodec payloadCodec;
  std::array<presonus::uc::ConnectionReceiveObserver, 2> observers{};
  struct Observer {
    Context *c;
    unsigned id;
  };
  std::array<Observer, 2> observerContext{};
  const char *name = "shadow-receiver";
  SocketConnection::Channel *socket = nullptr;
  void row(std::initializer_list<unsigned> v) {
    Row r{};
    std::copy(v.begin(), v.end(), r.begin());
    trace.push_back(r);
  }
  unsigned idFor(const Event &e) {
    for (unsigned i = 0; i < created; ++i)
      if (items[i] && &items[i]->value.header == &e)
        return i;
    std::abort();
  }
  presonus::uc::FactoryCodec codec() {
    presonus::uc::FactoryCodec v;
    v.context = this;
    v.create = [](void *p) -> EventItem * {
      auto &c = *static_cast<Context *>(p);
      require(!c.observerHeld && !c.queueHeld);
      ++c.allocCalls;
      if (c.allocNull) {
        c.row({5, none});
        return nullptr;
      }
      unsigned id = c.created++;
      require(id < 4);
      auto *i = new Item(&c, id);
      c.items[id] = i;
      c.row({5, id});
      return i;
    };
    v.read = [](void *p, EventItem *item, BufferReader &r) {
      auto &c = *static_cast<Context *>(p);
      auto *i = dynamic_cast<Item *>(item);
      c.row({6, i ? i->id : none});
      const auto &codec = c.payloadCodec.codec();
      return codec.read(codec.context, item, r);
    };
    v.destroy = [](void *, EventItem *i) { delete i; };
    return v;
  }
  void initializeBindings() {
    state.context = this;
    state.buffer = &buffer;
    state.connectionName = name;
    state.readable = [](void *p, int timeout) {
      auto &c = *static_cast<Context *>(p);
      require(timeout == 1);
      unsigned value =
          c.socket
              ? unsigned(c.socket->isReadable(timeout))
              : (c.readyCursor < c.ready.size() ? c.ready[c.readyCursor] : 0);
      ++c.readyCursor;
      c.row({1, 1, value});
      return bool(value);
    };
    state.available = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      unsigned value = c.socket ? unsigned(c.socket->getBytesAvailable())
                                : (c.availableCursor < c.available.size()
                                       ? c.available[c.availableCursor]
                                       : 0);
      ++c.availableCursor;
      c.row({2, value});
      return signedBits(value);
    };
    state.read = [](void *p, void *out, int count) {
      auto &c = *static_cast<Context *>(p);
      require(out == c.buffer.getAddress() && count >= 0 && count <= 16384);
      int result;
      unsigned copied;
      if (c.socket) {
        result = c.socket->read(out, count);
        copied = result > 0 ? unsigned(result) : 0;
      } else {
        Response response = c.readCursor < c.responses.size()
                                ? c.responses[c.readCursor]
                                : Response{-99, {}};
        require(response.data.size() ==
                    unsigned(std::max(0, response.result)) &&
                response.data.size() <= unsigned(count));
        if (!response.data.empty())
          std::memcpy(out, response.data.data(), response.data.size());
        result = response.result;
        copied = response.data.size();
      }
      ++c.readCursor;
      c.row({3, unsigned(count), unsigned(result), copied});
      return result;
    };
    state.factory = [](void *p) -> EventFactory & {
      auto &c = *static_cast<Context *>(p);
      c.row({4});
      return *c.factory;
    };
    state.lock = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      require(!c.observerHeld);
      c.actualObserverLock.lock();
      c.observerHeld = true;
      unsigned before = c.state.observerCount;
      if (c.lockOverride != noOverride)
        c.state.observerCount = signedBits(c.lockOverride);
      c.row({10, before, unsigned(c.state.observerCount)});
    };
    state.unlock = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      require(c.observerHeld);
      c.observerHeld = false;
      c.row({11});
      c.actualObserverLock.unlock();
    };
    for (unsigned i = 0; i < 2; ++i) {
      observerContext[i] = {this, i};
      observers[i].context = &observerContext[i];
      observers[i].received = [](void *p, int index, const Event &e,
                                 int transferred, const char *name) {
        auto &o = *static_cast<Observer *>(p);
        auto &c = *o.c;
        require(c.observerHeld && index == c.state.connectionIndex &&
                name == c.name);
        c.row({9, o.id, c.idFor(e), unsigned(index), unsigned(transferred),
               unsigned(c.state.receivedBytes),
               unsigned(c.state.receivedBytes >> 32),
               unsigned(c.state.receivedEvents)});
      };
    }
    state.observers = observers.data();
    state.append = [](void *p, EventItem *base) {
      auto &c = *static_cast<Context *>(p);
      auto *i = dynamic_cast<Item *>(base);
      require(i && c.items[i->id] == i && !c.observerHeld && !c.queueHeld);
      unsigned id = i->id;
      c.row({14, id});
      c.queueHeld = true;
      c.row({12});
      require(c.next[id] == none);
      if (!c.queue.empty()) {
        c.previous[id] = c.queue.back();
        c.next[c.queue.back()] = id;
      }
      c.queue.push_back(id);
      c.queueHeld = false;
      c.row({13});
    };
  }
  std::array<unsigned, 33> fields(bool returned) {
    unsigned alive = 0;
    for (unsigned i = 0; i < 4; ++i)
      if (items[i])
        alive |= 1u << i;
    std::array<unsigned, 4> order{none, none, none, none};
    require(queue.size() <= 4);
    std::copy(queue.begin(), queue.end(), order.begin());
    return {unsigned(returned),
            state.pending,
            state.magicBits,
            state.kindBits,
            state.length,
            unsigned(state.receivedBytes),
            unsigned(state.receivedBytes >> 32),
            unsigned(state.receivedEvents),
            unsigned(state.receivedEvents >> 32),
            unsigned(state.observerCount),
            readyCursor,
            availableCursor,
            readCursor,
            created,
            allocCalls,
            alive,
            unsigned(queue.size()),
            order[0],
            order[1],
            order[2],
            order[3],
            next[0],
            next[1],
            next[2],
            next[3],
            previous[0],
            previous[1],
            previous[2],
            previous[3],
            destroyed[0],
            destroyed[1],
            destroyed[2],
            destroyed[3]};
  }
  void cleanup() {
    recording = false;
    for (unsigned i = 0; i < 4; ++i)
      delete items[i];
  }
};
Item::~Item() {
  if (context->recording) {
    require(!context->observerHeld && !context->queueHeld);
    context->frozen[id] = snapshot(value);
    ++context->destroyed[id];
    context->row({7, id});
  }
  context->items[id] = nullptr;
}
Event &Item::getData() {
  context->row({8, id});
  return value.header;
}
static void composed() {
  presonus::uc::ParamValueFactoryCodec encoder;
  presonus::uc::CclFactoryRegistry actual_registry;
  auto &registry = actual_registry.registry();
  encoder.registerIn(registry);
  EventFactory writer(registry);
  ParamValueEvent v;
  v.header = {20566, 0, 0x1234, 0xabcd};
  std::strcpy(v.path.data(), "/receive");
  v.index = 65535;
  v.valueBits = 0x7fc00001;
  encoder.bind(v);
  std::array<char, 256> bytes{};
  int n = writer.write(bytes.data(), bytes.size(), v.header);
  require(n > 0);
  struct Stream {
    std::vector<unsigned char> data;
    unsigned cursor = 0, calls = 0;
  } stream;
  stream.data = {'U',
                 'C',
                 0,
                 1,
                 static_cast<unsigned char>(n),
                 static_cast<unsigned char>(n >> 8)};
  stream.data.insert(stream.data.end(), bytes.begin(), bytes.begin() + n);
  presonus::uc::SocketChannelIO io;
  io.context = &stream;
  io.readable = [](void *p, int timeout) {
    require(timeout == 1);
    auto &s = *static_cast<Stream *>(p);
    return s.cursor < s.data.size();
  };
  io.available = [](void *p, int &out) {
    auto &s = *static_cast<Stream *>(p);
    out = s.data.size() - s.cursor;
    return 0;
  };
  io.receive = [](void *p, void *out, int count, int flags) {
    auto &s = *static_cast<Stream *>(p);
    require(flags == 0 && count > 0);
    ++s.calls;
    if (s.calls % 3 != 0)
      return 0;
    unsigned take = std::min<unsigned>(
        {unsigned(count), 2u, unsigned(s.data.size() - s.cursor)});
    require(take);
    std::memcpy(out, s.data.data() + s.cursor, take);
    s.cursor += take;
    return int(take);
  };
  SocketConnection::Channel socket(io);
  Context c;
  c.state.observerCount = 2;
  c.socket = &socket;
  c.initializeBindings();
  auto codec = c.codec();
  presonus::uc::CclFactoryRegistry actual_reads;
  auto &reads = actual_reads.registry();
  reads.append(20566, &codec);
  EventFactory factory(reads);
  c.factory = &factory;
  presonus::uc::ConnectionState common;
  common.receive = &c.state;
  hierarchy_test::ConcreteConnection connection(common);
  require(connection.readEvents() && c.queue == std::vector<unsigned>({0}) &&
          c.state.receivedBytes == unsigned(n) && c.state.receivedEvents == 1 &&
          c.created == 1 && c.items[0]->value.valueBits == v.valueBits &&
          c.items[0]->value.index == 65535 && !c.state.pending &&
          stream.cursor == stream.data.size());
  c.cleanup();
  encoder.unbind(v);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 8> magic{};
  f.read(reinterpret_cast<char *>(magic.data()), 8);
  if (std::memcmp(magic.data(), "UCRXv001", 8))
    return 3;
  unsigned cases = readWord(f), invocations = 0;
  for (unsigned index = 0; index < cases; ++index) {
    std::array<unsigned, 13> in{};
    for (auto &v : in)
      v = readWord(f);
    Context c;
    c.state.pending = in[0];
    c.state.magicBits = in[1];
    c.state.kindBits = in[2];
    c.state.length = in[3];
    c.state.connectionIndex = signedBits(in[4]);
    c.state.observerCount = signedBits(in[5]);
    c.lockOverride = in[6];
    c.allocNull = in[7];
    unsigned calls = in[8];
    c.state.receivedBytes =
        std::uint64_t(in[9]) | (std::uint64_t(in[10]) << 32);
    c.state.receivedEvents =
        std::uint64_t(in[11]) | (std::uint64_t(in[12]) << 32);
    f.read(reinterpret_cast<char *>(c.buffer.getAddress()), c.buffer.getSize());
    unsigned count = readWord(f);
    for (unsigned i = 0; i < count; ++i)
      c.ready.push_back(readWord(f));
    count = readWord(f);
    for (unsigned i = 0; i < count; ++i)
      c.available.push_back(readWord(f));
    count = readWord(f);
    for (unsigned i = 0; i < count; ++i) {
      int result = signedBits(readWord(f));
      unsigned n = readWord(f);
      Response r{result, std::vector<unsigned char>(n)};
      if (n)
        f.read(reinterpret_cast<char *>(r.data.data()), n);
      c.responses.push_back(std::move(r));
    }
    require(f.good());
    c.initializeBindings();
    auto codec = c.codec();
    presonus::uc::CclFactoryRegistry actual_registry;
    auto &registry = actual_registry.registry();
    registry.append(20566, &codec);
    EventFactory factory(registry);
    c.factory = &factory;
    presonus::uc::ConnectionState common;
    common.receive = &c.state;
    hierarchy_test::ConcreteConnection connection(common);
    for (unsigned call = 0; call < calls; ++call) {
      std::array<unsigned, 33> expected{};
      for (auto &v : expected)
        v = readWord(f);
      std::array<unsigned char, bufferSize> buffer{};
      f.read(reinterpret_cast<char *>(buffer.data()), buffer.size());
      unsigned rows = readWord(f);
      std::vector<Row> trace(rows);
      for (auto &r : trace)
        for (auto &v : r)
          v = readWord(f);
      std::array<Body, 4> bodies{};
      for (auto &b : bodies)
        f.read(reinterpret_cast<char *>(b.data()), b.size());
      if (!f)
        return 4;
      c.trace.clear();
      bool result = connection.readEvents();
      auto actual = c.fields(result);
      if (actual != expected || c.trace != trace || c.observerHeld ||
          c.queueHeld) {
        unsigned at = 0;
        while (at < 33 && actual[at] == expected[at])
          ++at;
        std::fprintf(stderr,
                     "case%u call%u scalar/trace mismatch word%u got%08x "
                     "want%08x trace%zu/%zu\n",
                     index, call, at, at < 33 ? actual[at] : 0,
                     at < 33 ? expected[at] : 0, c.trace.size(), trace.size());
        return 5;
      }
      if (std::memcmp(c.buffer.getAddress(), buffer.data(), bufferSize)) {
        std::fprintf(stderr, "case%u call%u packet-buffer mismatch\n", index,
                     call);
        return 6;
      }
      for (unsigned i = 0; i < 4; ++i) {
        Body body = c.items[i] ? snapshot(c.items[i]->value) : c.frozen[i];
        if (body != bodies[i]) {
          std::fprintf(
              stderr, "case%u call%u item%u partialdecode/ownership mismatch\n",
              index, call, i);
          return 7;
        }
      }
      ++invocations;
    }
    c.cleanup();
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 8;
  composed();
  std::printf("%u original ARM receive cases/%u invocations passed with actual "
              "factory/PV decoding\n1 composed virtual SocketChannel "
              "framing/raw-bits/ownership group passed\n",
              cases, invocations);
}
