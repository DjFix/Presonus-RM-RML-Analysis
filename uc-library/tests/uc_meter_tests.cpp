#include "presonus/uc/meter_events.hpp"
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
    p[i] = static_cast<unsigned char>(v >> (i * 8));
}
static unsigned short get16(const unsigned char *p) {
  return static_cast<unsigned short>(p[0] | (unsigned(p[1]) << 8));
}
static void put16(unsigned char *p, unsigned short v) {
  p[0] = static_cast<unsigned char>(v);
  p[1] = static_cast<unsigned char>(v >> 8);
}
static void read(std::istream &in, void *p, std::size_t size) {
  if (!in.read(static_cast<char *>(p), static_cast<std::streamsize>(size)))
    throw std::runtime_error("truncated fixture");
}
static std::uint32_t word(std::istream &in) {
  unsigned char bytes[4];
  read(in, bytes, 4);
  return get32(bytes);
}
template <class Bytes> static void pattern(Bytes &bytes, unsigned seed) {
  for (std::size_t i = 0; i < bytes.size(); ++i)
    bytes[i] = static_cast<unsigned char>(i * 29 + seed * 71);
}
template <class Bytes> static void patch(std::istream &in, Bytes &bytes) {
  auto count = word(in);
  if (count > bytes.size())
    throw std::runtime_error("invalid patch count");
  std::uint32_t end = 0;
  for (std::uint32_t i = 0; i < count; ++i) {
    auto start = word(in), size = word(in);
    if (start < end || start > bytes.size() || size > bytes.size() - start)
      throw std::runtime_error("invalid patch range");
    read(in, bytes.data() + start, size);
    end = start + size;
  }
}
template <class T> static void load(T &value, const Image &image) {
  value.header = {get32(image.data()), get32(image.data() + 4),
                  get32(image.data() + 8), get32(image.data() + 12)};
  value.keyBits = get32(image.data() + 16);
  value.source = get16(image.data() + 20);
  value.count = get16(image.data() + 22);
  value.recordCount = image[24];
  value.reserved25 = image[25];
  for (unsigned i = 0; i < 36; ++i)
    value.records[i] = {get16(image.data() + 26 + 6 * i),
                        get16(image.data() + 28 + 6 * i),
                        get16(image.data() + 30 + 6 * i)};
  std::memcpy(value.data.data(), image.data() + 242, value.data.size());
}
template <class T> static void save(Image &image, const T &value) {
  put32(image.data(), value.header.type);
  put32(image.data() + 4, value.header.reserved04);
  put32(image.data() + 8, value.header.routeA);
  put32(image.data() + 12, value.header.routeB);
  put32(image.data() + 16, value.keyBits);
  put16(image.data() + 20, value.source);
  put16(image.data() + 22, value.count);
  image[24] = value.recordCount;
  image[25] = value.reserved25;
  for (unsigned i = 0; i < 36; ++i) {
    put16(image.data() + 26 + 6 * i, value.records[i].a);
    put16(image.data() + 28 + 6 * i, value.records[i].b);
    put16(image.data() + 30 + 6 * i, value.records[i].c);
  }
  std::memcpy(image.data() + 242, value.data.data(), value.data.size());
}
template <class T, int Type> struct Context {
  T *value;
  int mode;
  int calls = 0;
  static bool write(void *p, BufferWriter &writer, const Event &event) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("write binding");
    return c.mode ? c.mode == 2
                  : MeterEventClass<T, Type>().write(writer, *c.value);
  }
  static bool read(void *p, Event &event, BufferReader &reader) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("read binding");
    return c.mode ? c.mode == 2
                  : MeterEventClass<T, Type>().read(*c.value, reader);
  }
};
template <class T, int Type>
static bool execute(Image &image, BufferReader &reader, BufferWriter &writer,
                    unsigned op, unsigned mode, int expectedCalls) {
  T value;
  load(value, image);
  Context<T, Type> context{&value, int(mode)};
  PrimitiveEventClass<T, Type> dispatch(
      {&context, Context<T, Type>::write, Context<T, Type>::read});
  bool result = op < 4
                    ? (op % 2 ? MeterEventClass<T, Type>().read(value, reader)
                              : MeterEventClass<T, Type>().write(writer, value))
                    : (op % 2 ? dispatch.read(value.header, reader)
                              : dispatch.write(writer, value.header));
  if (op >= 4 && context.calls != expectedCalls)
    throw std::runtime_error("meter virtual callback count");
  save(image, value);
  return result;
}
template <class T, int Type> static void telemetry() {
  using namespace presonus::uc;
  using Codec = MeterEventClass<T, Type>;
  for (unsigned count : {0U, 1U, 1024U})
    for (unsigned groups : {0U, 1U, 36U}) {
      T value;
      value.header = {Type, 0, 17, 29};
      value.keyBits = 0x80ff0011;
      value.source = 65535;
      value.count = static_cast<unsigned short>(count);
      value.recordCount = static_cast<unsigned char>(groups);
      for (std::size_t i = 0; i < value.data.size(); ++i)
        value.data[i] = static_cast<unsigned char>(i * 29 + 71);
      for (unsigned i = 0; i < 36; ++i)
        value.records[i] = {static_cast<unsigned short>(i),
                            static_cast<unsigned short>(65535 - i),
                            static_cast<unsigned short>(32768 + i)};
      TypedFactoryCodec<T, Codec, Type> adapter;
      adapter.bind(value);
      FactoryRegistry registry;
      adapter.registerIn(registry);
      EventFactory factory(registry);
      std::array<char, 4096> wire{};
      int size = factory.write(wire.data(), 4096, value.header);
      int expected = 6 + 8 + int(count) * T::sampleWidth + 1 + int(groups) * 6;
      if (size != expected)
        throw std::runtime_error("telemetry encode length");
      BufferReader reader(wire.data(), size);
      auto *item = dynamic_cast<TypedEventItem<T> *>(factory.read(reader));
      if (!item || reader.position() != size ||
          item->value.header.type != Type || item->value.header.routeA != 17 ||
          item->value.header.routeB != 29 ||
          item->value.keyBits != value.keyBits || item->value.source != 65535 ||
          item->value.count != count || item->value.recordCount != groups)
        throw std::runtime_error("telemetry decode fields");
      if (std::memcmp(item->value.data.data(), value.data.data(),
                      count * T::sampleWidth))
        throw std::runtime_error("telemetry raw sample bytes");
      for (unsigned i = 0; i < groups; ++i)
        if (item->value.records[i].a != value.records[i].a ||
            item->value.records[i].b != value.records[i].b ||
            item->value.records[i].c != value.records[i].c)
          throw std::runtime_error("telemetry record words");
      if (factory.create(item->getData()) != nullptr)
        throw std::runtime_error("telemetry returned binding contract");
      adapter.bind(item->value);
      std::array<char, 4096> rewrite{};
      if (factory.write(rewrite.data(), 4096, item->getData()) != size ||
          rewrite != wire)
        throw std::runtime_error("telemetry read bind write");
      auto *copy = factory.create(item->getData());
      if (!copy)
        throw std::runtime_error("telemetry bound clone");
      delete copy;
      adapter.unbind(item->value);
      delete item;
      // Original meter codecs intentionally report success after truncated
      // tails.
      BufferReader truncated(wire.data(), size - 1);
      auto *partial =
          dynamic_cast<TypedEventItem<T> *>(factory.read(truncated));
      if (!partial || partial->value.count != count)
        throw std::runtime_error("meter truncated tail must remain accepted");
      if (groups) {
        if (partial->value.recordCount != groups ||
            partial->value.records[groups - 1].c != 0 ||
            truncated.position() != size - 2)
          throw std::runtime_error("meter partial last word");
      } else if (partial->value.recordCount != 0 ||
                 truncated.position() != size - 1)
        throw std::runtime_error("meter missing record count");
      delete partial;
      if (count) {
        BufferReader shortData(wire.data(),
                               14 + int(count) * T::sampleWidth - 1);
        if (factory.read(shortData) != nullptr || shortData.position() != 14)
          throw std::runtime_error("meter sample truncation rejection");
      }
      auto *blank = dynamic_cast<TypedEventItem<T> *>(factory.createType(Type));
      if (!blank)
        throw std::runtime_error("meter createType");
      adapter.bind(blank->value);
      auto *blankCopy =
          dynamic_cast<TypedEventItem<T> *>(factory.create(blank->getData()));
      if (!blankCopy)
        throw std::runtime_error("meter createType clone");
      adapter.bind(blankCopy->value);
      if (factory.write(rewrite.data(), 4096, blankCopy->getData()) != 15)
        throw std::runtime_error("meter blank write");
      adapter.unbind(blankCopy->value);
      delete blankCopy;
      adapter.unbind(blank->value);
      delete blank;
      adapter.unbind(value);
    }
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCMRv001", 8))
    return 3;
  auto count = word(in);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[24];
    read(in, meta, 24);
    auto op = meta[1], mode = meta[3];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12), ioSize = get32(meta + 16),
         seed = get32(meta + 20);
    if (ioSize < capacity || ioSize > 131351 || offset > capacity || op > 7 ||
        mode > 2)
      throw std::runtime_error("invalid fixture metadata");
    std::vector<unsigned char> io(ioSize);
    Image event;
    pattern(io, seed);
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
    bool result = (op / 2) % 2
                      ? execute<MeterEvent16, 19795>(event, reader, writer, op,
                                                     mode, calls)
                      : execute<MeterEvent8, 19778>(event, reader, writer, op,
                                                    mode, calls);
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
    return 4;
  telemetry<MeterEvent8, 19778>();
  telemetry<MeterEvent16, 19795>();
  std::cout
      << count
      << " original ARM meter fixtures passed\n18 composed telemetry "
         "count/record/read-write/clone/create/partial-tail cases passed\n";
}
