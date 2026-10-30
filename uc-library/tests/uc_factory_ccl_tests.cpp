#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/event_factory.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace Presonus::UC;
using namespace presonus::uc;
static std::uint32_t get32(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static int signedBits(std::uint32_t bits) {
  int value;
  std::memcpy(&value, &bits, 4);
  return value;
}
static void read(std::istream &in, void *p, std::size_t n) {
  if (!in.read(static_cast<char *>(p), static_cast<std::streamsize>(n)))
    throw std::runtime_error("truncated fixture");
}
namespace presonus::uc::test {
struct Item : EventItem {
  Event value;
  Event &getData() override { return value; }
};
struct State {
  Item item;
  std::uint32_t marker = 0xdeadbeef;
  std::vector<int> trace;
  int writeflag, readflag, allocnull, clonenull;
  int lastcursor = -1;
};
struct Context {
  State *state;
  int id;
};
static EventItem *create(void *raw) {
  auto &c = *static_cast<Context *>(raw);
  c.state->trace.push_back(10 + c.id);
  return c.state->allocnull ? nullptr : &c.state->item;
}
static EventItem *clone(void *raw, const Event &) {
  auto &c = *static_cast<Context *>(raw);
  c.state->trace.push_back(20 + c.id);
  return c.state->clonenull ? nullptr : &c.state->item;
}
static bool write(void *raw, BufferWriter &writer, const Event &) {
  auto &c = *static_cast<Context *>(raw);
  c.state->trace.push_back(30 + c.id);
  unsigned char a[2] = {static_cast<unsigned char>(0x41 + c.id), 0x80},
                b[3] = {static_cast<unsigned char>(0x51 + c.id), 0, 0xff};
  bool result = writer.writeRaw(a, 2) && writer.writeRaw(b, 3);
  c.state->lastcursor = writer.position();
  return result && c.state->writeflag;
}
static bool decode(void *raw, EventItem *item, BufferReader &reader) {
  auto &c = *static_cast<Context *>(raw);
  c.state->trace.push_back(40 + c.id);
  unsigned char a[2]{}, b[3]{};
  bool result = reader.readRaw(a, 2);
  if (result) {
    if (item)
      c.state->marker ^= std::uint32_t(a[0]) | (std::uint32_t(a[1]) << 8);
    result = reader.readRaw(b, 3);
    if (result && item)
      c.state->marker ^= std::uint32_t(b[0]) | (std::uint32_t(b[1]) << 8) |
                         (std::uint32_t(b[2]) << 16);
  }
  c.state->lastcursor = reader.position();
  return result && c.state->readflag;
}
static void destroy(void *raw, EventItem *item) {
  auto &c = *static_cast<Context *>(raw);
  if (item != &c.state->item)
    throw std::runtime_error("unexpected delete item");
  c.state->trace.push_back(50 + c.id);
}

// Independent typed adapter demonstrates complete tag/header/payload routing.
// It uses composition and explicit context, never a fabricated Event downcast.
struct ValueItem : EventItem {
  ParamValueEvent value;
  Event &getData() override { return value.header; }
};
struct ValueContext {
  ValueItem outbound;
  int deletes = 0;
};
static EventItem *valueCreate(void *) {
  auto *p = new ValueItem;
  p->value.header.type = 20566;
  return p;
}
static EventItem *valueClone(void *raw, const Event &event) {
  auto &c = *static_cast<ValueContext *>(raw);
  if (&event != &c.outbound.value.header)
    throw std::runtime_error("unbound outbound event");
  return new ValueItem(c.outbound);
}
static bool valueWrite(void *raw, BufferWriter &writer, const Event &event) {
  auto &c = *static_cast<ValueContext *>(raw);
  if (&event != &c.outbound.value.header)
    throw std::runtime_error("unbound outbound event");
  return EventClass().write(writer, event) &&
         ParamValueEventClass().write(writer, c.outbound.value);
}
static bool valueRead(void *, EventItem *item, BufferReader &reader) {
  auto *p = dynamic_cast<ValueItem *>(item);
  return p && EventClass().read(p->value.header, reader) &&
         ParamValueEventClass().read(p->value, reader);
}
static void valueDelete(void *raw, EventItem *item) {
  ++static_cast<ValueContext *>(raw)->deletes;
  delete item;
}
static void composition() {
  ValueContext context;
  auto &v = context.outbound.value;
  v.header = {20566, 0, 17, 29};
  std::memcpy(v.path.data(), "gain", 5);
  v.index = 65535;
  v.valueBits = 0x7f812345;
  FactoryCodec codec{&context,   valueCreate, valueClone,
                     valueWrite, valueRead,   valueDelete};
  CclFactoryRegistry actualRegistry;
  FactoryRegistry &registry = actualRegistry.registry();
  registry.append(20566, &codec);
  EventFactory factory(registry);
  std::array<char, 64> data{};
  int size = factory.write(data.data(), 64, v.header);
  if (size != 17)
    throw std::runtime_error("composed write length");
  auto *item = dynamic_cast<ValueItem *>(factory.read(data.data(), size));
  if (!item || item->value.header.type != 20566 ||
      item->value.header.routeA != 17 || item->value.header.routeB != 29 ||
      item->value.index != 65535 || item->value.valueBits != 0x7f812345 ||
      std::memcmp(item->value.path.data(), "gain", 5))
    throw std::runtime_error("composed decode");
  delete item;
  if (factory.write(data.data(), 8, v.header) != 6)
    throw std::runtime_error("ignored payload failure length");
  if (factory.read(data.data(), 6) != nullptr || context.deletes != 1)
    throw std::runtime_error("composed failed read cleanup");
  auto *copied = dynamic_cast<ValueItem *>(factory.create(v.header));
  if (!copied || copied->value.valueBits != v.valueBits)
    throw std::runtime_error("composed clone");
  delete copied;
}
} // namespace presonus::uc::test
int main(int argc, char **argv) {
  using namespace presonus::uc::test;
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCFAv001", 8))
    return 3;
  unsigned char countbytes[4];
  read(in, countbytes, 4);
  auto count = get32(countbytes);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char metadata[96];
    read(in, metadata, 96);
    int m[24];
    for (int i = 0; i < 24; ++i)
      m[i] = signedBits(get32(metadata + 4 * i));
    std::array<unsigned char, 64> io, expected;
    read(in, io.data(), 64);
    read(in, expected.data(), 64);
    State state;
    state.writeflag = m[6];
    state.readflag = m[7];
    state.allocnull = m[8];
    state.clonenull = m[9];
    Context contexts[3] = {{&state, 0}, {&state, 1}, {&state, 2}};
    FactoryCodec codecs[3];
    for (int i = 0; i < 3; ++i)
      codecs[i] = {contexts + i, create, clone, write, decode, destroy};
    CclFactoryRegistry actualRegistry;
    FactoryRegistry &registry = actualRegistry.registry();
    int type = m[4], scenario = m[5];
    if (scenario == 2 || scenario == 3 || scenario == 5 || scenario == 6)
      registry.fallback = codecs;
    if (scenario == 1 || scenario == 6)
      registry.append(type, codecs + 1);
    if (scenario == 3 || scenario == 7)
      registry.append(type, nullptr);
    int collision = signedBits(std::uint32_t(type) ^ 8);
    if (scenario == 4) {
      registry.append(collision, codecs + 2);
      registry.append(type, codecs + 1);
      registry.append(type, codecs + 2);
    }
    if (scenario == 5)
      registry.append(collision, codecs + 2);
    EventFactory factory(registry);
    Event event;
    event.type = std::uint32_t(type);
    BufferReader reader(io.data(), m[2], m[3]);
    BufferWriter writer(io.data(), m[2], m[3]);
    int result = 0, cursor = m[3];
    switch (m[1]) {
    case 0:
      result = EventFactory::hashEventType(type, m[10]);
      break;
    case 1:
      result = factory.create(event) != nullptr;
      break;
    case 2:
      result = factory.createType(type) != nullptr;
      break;
    case 3:
      result = factory.write(writer, event);
      cursor = writer.position();
      break;
    case 4:
      result = factory.write(reinterpret_cast<char *>(io.data()), m[2], event);
      cursor = state.lastcursor < 0 ? 0 : state.lastcursor;
      break;
    case 5:
      result = factory.read(reader) != nullptr;
      cursor = reader.position();
      break;
    case 6:
      result = factory.read(reinterpret_cast<const char *>(io.data()), m[2]) !=
               nullptr;
      cursor = state.lastcursor < 0 ? (m[2] >= 2 ? 2 : 0) : state.lastcursor;
      break;
    default:
      return 4;
    }
    std::vector<int> trace(m + 14, m + 14 + m[13]);
    if (result != m[11] || cursor != m[12] || state.trace != trace ||
        state.marker != std::uint32_t(m[22]) || io != expected) {
      std::cerr << "mismatch row=" << row << " role=" << m[0] << " op=" << m[1]
                << " capacity=" << m[2] << " offset=" << m[3]
                << " type=" << type << " scenario=" << scenario
                << " result=" << result << '/' << m[11] << " cursor=" << cursor
                << '/' << m[12] << " trace=" << (state.trace == trace)
                << " marker=" << (state.marker == std::uint32_t(m[22]))
                << " bytes=" << (io == expected) << '\n';
      return 1;
    }
  }
  if (in.peek() != std::char_traits<char>::eof())
    return 5;
  composition();
  std::cout << count
            << " original ARM factory fixtures passed\n3 composed "
               "parameter-event routing/clone/failure checks passed\n";
}
