#include "presonus/uc/parameter_events.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace Presonus::UC;
using Image = std::array<unsigned char, 2336>;
static std::uint32_t get32(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static void put32(unsigned char *p, std::uint32_t v) {
  for (int i = 0; i < 4; ++i)
    p[i] = static_cast<unsigned char>(v >> (8 * i));
}
static unsigned short get16(const unsigned char *p) {
  return static_cast<unsigned short>(p[0] | (unsigned(p[1]) << 8));
}
static void put16(unsigned char *p, unsigned short v) {
  p[0] = static_cast<unsigned char>(v);
  p[1] = static_cast<unsigned char>(v >> 8);
}
static void read(std::istream &in, void *p, std::size_t n) {
  if (!in.read(static_cast<char *>(p), static_cast<std::streamsize>(n)))
    throw std::runtime_error("truncated fixture");
}
static std::uint32_t word(std::istream &in) {
  unsigned char p[4];
  read(in, p, 4);
  return get32(p);
}
template <class Bytes> static void pattern(Bytes &b, unsigned seed) {
  for (std::size_t i = 0; i < b.size(); ++i)
    b[i] = static_cast<unsigned char>((i * 29 + seed * 17) % 255 + 1);
}
template <class Bytes> static void patch(std::istream &in, Bytes &b) {
  auto n = word(in);
  if (n > b.size())
    throw std::runtime_error("invalid patch count");
  std::uint32_t end = 0;
  for (std::uint32_t i = 0; i < n; ++i) {
    auto start = word(in), size = word(in);
    if (start < end || start > b.size() || size > b.size() - start)
      throw std::runtime_error("invalid patch range");
    read(in, b.data() + start, size);
    end = start + size;
  }
}
static void loadPayload(ParamEditEvent &, const Image &) {}
static void savePayload(Image &, const ParamEditEvent &) {}
static void loadPayload(ParamModeEvent &v, const Image &b) {
  std::memcpy(v.modeBytes.data(), b.data() + 146, 64);
}
static void savePayload(Image &b, const ParamModeEvent &v) {
  std::memcpy(b.data() + 146, v.modeBytes.data(), 64);
}
static void loadPayload(ParamIncrementEvent &v, const Image &b) {
  v.incrementBits = get16(b.data() + 146);
}
static void savePayload(Image &b, const ParamIncrementEvent &v) {
  put16(b.data() + 146, v.incrementBits);
}
static void loadPayload(ParamColorEvent &v, const Image &b) {
  std::memcpy(v.reserved92.data(), b.data() + 146, 2);
  v.colorBits = get32(b.data() + 148);
}
static void savePayload(Image &b, const ParamColorEvent &v) {
  std::memcpy(b.data() + 146, v.reserved92.data(), 2);
  put32(b.data() + 148, v.colorBits);
}
static void loadPayload(ParamRangeEvent &v, const Image &b) {
  std::memcpy(v.reserved92.data(), b.data() + 146, 2);
  for (int i = 0; i < 5; ++i)
    v.wordBits[i] = get32(b.data() + 148 + 4 * i);
  for (int i = 0; i < 2; ++i)
    std::memcpy(v.labels[i].data(), b.data() + 168 + 32 * i, 32);
}
static void savePayload(Image &b, const ParamRangeEvent &v) {
  std::memcpy(b.data() + 146, v.reserved92.data(), 2);
  for (int i = 0; i < 5; ++i)
    put32(b.data() + 148 + 4 * i, v.wordBits[i]);
  for (int i = 0; i < 2; ++i)
    std::memcpy(b.data() + 168 + 32 * i, v.labels[i].data(), 32);
}
static void loadPayload(ParamStringListEvent &v, const Image &b) {
  std::memcpy(v.reserved92.data(), b.data() + 146, 2);
  v.listFieldBits = get32(b.data() + 148);
  std::memcpy(v.text.data(), b.data() + 152, 1024);
}
static void savePayload(Image &b, const ParamStringListEvent &v) {
  std::memcpy(b.data() + 146, v.reserved92.data(), 2);
  put32(b.data() + 148, v.listFieldBits);
  std::memcpy(b.data() + 152, v.text.data(), 1024);
}
template <class T> static void load(T &v, const Image &b) {
  v.header = {get32(b.data()), get32(b.data() + 4), get32(b.data() + 8),
              get32(b.data() + 12)};
  std::memcpy(v.path.data(), b.data() + 16, 128);
  v.index = get16(b.data() + 144);
  loadPayload(v, b);
}
template <class T> static void save(Image &b, const T &v) {
  put32(b.data(), v.header.type);
  put32(b.data() + 4, v.header.reserved04);
  put32(b.data() + 8, v.header.routeA);
  put32(b.data() + 12, v.header.routeB);
  std::memcpy(b.data() + 16, v.path.data(), 128);
  put16(b.data() + 144, v.index);
  savePayload(b, v);
}
template <class T, class Codec> struct Context {
  T *value;
  int mode;
  int calls = 0;
  static bool write(void *p, BufferWriter &writer, const Event &event) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("write binding");
    return c.mode ? c.mode == 2 : Codec().write(writer, *c.value);
  }
  static bool read(void *p, Event &event, BufferReader &reader) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("read binding");
    return c.mode ? c.mode == 2 : Codec().read(*c.value, reader);
  }
};
template <class T, class Codec, int Type>
static bool execute(Image &b, BufferReader &reader, BufferWriter &writer,
                    unsigned op, unsigned mode, int expectedCalls) {
  T value;
  load(value, b);
  Context<T, Codec> context{&value, int(mode)};
  PrimitiveEventClass<T, Type> dispatch(
      {&context, Context<T, Codec>::write, Context<T, Codec>::read});
  bool result = op < 12 ? (op % 2 ? Codec().read(value, reader)
                                  : Codec().write(writer, value))
                        : (op % 2 ? dispatch.read(value.header, reader)
                                  : dispatch.write(writer, value.header));
  if (op >= 12 && context.calls != expectedCalls)
    throw std::runtime_error("parameter virtual callback count");
  save(b, value);
  return result;
}
template <class T, class Codec, int Type> static void integration(T value) {
  using namespace presonus::uc;
  value.header = {Type, 0, 17, 29};
  TypedFactoryCodec<T, Codec, Type> adapter;
  adapter.bind(value);
  FactoryRegistry registry;
  adapter.registerIn(registry);
  EventFactory factory(registry);
  std::array<char, 2048> wire{};
  int size = factory.write(wire.data(), 2048, value.header);
  if (size < 6)
    throw std::runtime_error("parameter encode");
  BufferReader reader(wire.data(), size);
  auto *item = dynamic_cast<TypedEventItem<T> *>(factory.read(reader));
  if (!item || reader.position() != size || item->value.header.type != Type ||
      item->value.header.routeA != 17 || item->value.header.routeB != 29)
    throw std::runtime_error("parameter decode");
  std::array<unsigned char, 2048> expected{}, actual{};
  BufferWriter ew(expected.data(), 2048), aw(actual.data(), 2048);
  if (!Codec().write(ew, value) || !Codec().write(aw, item->value) ||
      ew.position() != aw.position() || expected != actual)
    throw std::runtime_error("parameter raw payload");
  std::array<char, 2048> rewritten{};
  if (factory.create(item->getData()) != nullptr ||
      factory.write(rewritten.data(), 2048, item->getData()) != 6)
    throw std::runtime_error("returned parameter binding contract");
  adapter.bind(item->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, item->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("bound parameter read write");
  auto *clone =
      dynamic_cast<TypedEventItem<T> *>(factory.create(item->getData()));
  if (!clone)
    throw std::runtime_error("bound parameter clone");
  adapter.bind(clone->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, clone->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("parameter clone bits");
  adapter.unbind(clone->value);
  delete clone;
  adapter.unbind(item->value);
  delete item;
  BufferReader truncated(wire.data(), size - 1);
  if (factory.read(truncated) != nullptr)
    throw std::runtime_error("parameter truncated payload acceptance");
  auto *blank = dynamic_cast<TypedEventItem<T> *>(factory.createType(Type));
  if (!blank)
    throw std::runtime_error("parameter createType");
  adapter.bind(blank->value);
  auto *copy =
      dynamic_cast<TypedEventItem<T> *>(factory.create(blank->getData()));
  if (!copy)
    throw std::runtime_error("parameter createType clone");
  adapter.bind(copy->value);
  if (factory.write(rewritten.data(), 2048, copy->getData()) < 6)
    throw std::runtime_error("parameter blank write");
  adapter.unbind(copy->value);
  delete copy;
  adapter.unbind(blank->value);
  delete blank;
  adapter.unbind(value);
}
template <std::size_t N> static void text(std::array<char, N> &b, unsigned n) {
  for (unsigned i = 0; i < n; ++i)
    b[i] = char((i * 29 + 17) % 255 + 1);
  b[n] = 0;
}
static void integrations() {
  const std::uint32_t bits[8] = {0,          0x80000000, 0x7f800000, 0xff800000,
                                 0x7fc12345, 0x7f812345, 0xffffffff, 1};
  for (unsigned variant = 0; variant < 4; ++variant) {
    unsigned pathlen[4] = {0, 1, 7, 127};
    unsigned short index[4] = {0, 32767, 32768, 65535};
    ParamEditEvent edit;
    text(edit.path, pathlen[variant]);
    edit.index = index[variant];
    integration<ParamEditEvent, ParamEditEventClass, 20549>(edit);
    ParamModeEvent mode;
    text(mode.path, pathlen[variant]);
    mode.index = index[variant];
    unsigned moden[4] = {0, 1, 7, 63};
    text(mode.modeBytes, moden[variant]);
    integration<ParamModeEvent, ParamModeEventClass, 20557>(mode);
    ParamIncrementEvent increment;
    text(increment.path, pathlen[variant]);
    increment.index = index[variant];
    increment.incrementBits = index[variant];
    integration<ParamIncrementEvent, ParamIncrementEventClass, 20553>(
        increment);
    ParamColorEvent color;
    text(color.path, pathlen[variant]);
    color.index = index[variant];
    color.colorBits = bits[variant + 3];
    integration<ParamColorEvent, ParamColorEventClass, 20547>(color);
    ParamRangeEvent range;
    text(range.path, pathlen[variant]);
    range.index = index[variant];
    for (unsigned i = 0; i < 5; ++i)
      range.wordBits[i] = bits[(variant + i) % 8];
    unsigned labeln[4] = {0, 1, 7, 31};
    text(range.labels[0], labeln[variant]);
    text(range.labels[1], labeln[(variant + 1) % 4]);
    integration<ParamRangeEvent, ParamRangeEventClass, 20562>(range);
    ParamStringListEvent list;
    text(list.path, pathlen[variant]);
    list.index = index[variant];
    list.listFieldBits = bits[variant + 4];
    unsigned listn[4] = {0, 1, 31, 1023};
    text(list.text, listn[variant]);
    integration<ParamStringListEvent, ParamStringListEventClass, 20556>(list);
  }
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCPAv001", 8))
    return 3;
  auto count = word(in);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[24];
    read(in, meta, 24);
    auto op = meta[1], mode = meta[3];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12), size = get32(meta + 16),
         seed = get32(meta + 20);
    if (size < capacity || size > 2071 || offset > capacity || op > 23 ||
        mode > 2)
      throw std::runtime_error("invalid parameter metadata");
    std::vector<unsigned char> io(size);
    Image event;
    pattern(io, seed + 11);
    pattern(event, seed + 1);
    patch(in, io);
    patch(in, event);
    auto expectedIo = io;
    auto expectedEvent = event;
    patch(in, expectedIo);
    patch(in, expectedEvent);
    BufferReader reader(io.data(), int(capacity), int(offset));
    BufferWriter writer(io.data(), int(capacity), int(offset));
    int calls = capacity - offset >= (op % 2 ? 4 : 6) ? 1 : 0;
    bool result = false;
    switch ((op % 12) / 2) {
    case 0:
      result = execute<ParamEditEvent, ParamEditEventClass, 20549>(
          event, reader, writer, op, mode, calls);
      break;
    case 1:
      result = execute<ParamModeEvent, ParamModeEventClass, 20557>(
          event, reader, writer, op, mode, calls);
      break;
    case 2:
      result = execute<ParamIncrementEvent, ParamIncrementEventClass, 20553>(
          event, reader, writer, op, mode, calls);
      break;
    case 3:
      result = execute<ParamColorEvent, ParamColorEventClass, 20547>(
          event, reader, writer, op, mode, calls);
      break;
    case 4:
      result = execute<ParamRangeEvent, ParamRangeEventClass, 20562>(
          event, reader, writer, op, mode, calls);
      break;
    case 5:
      result = execute<ParamStringListEvent, ParamStringListEventClass, 20556>(
          event, reader, writer, op, mode, calls);
      break;
    default:
      return 4;
    }
    int cursor = op % 2 ? reader.position() : writer.position();
    if (result != bool(meta[2]) || cursor != int(next) || io != expectedIo ||
        event != expectedEvent) {
      std::cerr << "mismatch row=" << row << " role=" << unsigned(meta[0])
                << " op=" << unsigned(op) << " mode=" << unsigned(mode)
                << " capacity=" << capacity << " offset=" << offset
                << " result=" << result << '/' << unsigned(meta[2])
                << " cursor=" << cursor << '/' << next
                << " IO=" << (io == expectedIo)
                << " event=" << (event == expectedEvent) << '\n';
      return 1;
    }
  }
  if (in.peek() != std::char_traits<char>::eof())
    return 5;
  integrations();
  std::cout << count
            << " original ARM parameter fixtures passed\n24 composed parameter "
               "routing/raw-bit/clone/create/binding/truncation cases passed\n";
}
