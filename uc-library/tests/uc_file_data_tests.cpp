#include "presonus/uc/file_data_events.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace Presonus::UC;
using Image = std::array<unsigned char, 8192>;
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
    b[i] = static_cast<unsigned char>(i * 29 + seed * 71);
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
static void load(FileDataEvent &v, const Image &b) {
  v.header = {get32(b.data()), get32(b.data() + 4), get32(b.data() + 8),
              get32(b.data() + 12)};
  v.idBits = get32(b.data() + 16);
  for (int i = 0; i < 2; ++i)
    v.wordBits[i] = get32(b.data() + 20 + 4 * i);
  v.partBits = get16(b.data() + 28);
  v.count = get16(b.data() + 30);
  std::memcpy(v.data.data(), b.data() + 32, 4096);
}
static void save(Image &b, const FileDataEvent &v) {
  put32(b.data(), v.header.type);
  put32(b.data() + 4, v.header.reserved04);
  put32(b.data() + 8, v.header.routeA);
  put32(b.data() + 12, v.header.routeB);
  put32(b.data() + 16, v.idBits);
  for (int i = 0; i < 2; ++i)
    put32(b.data() + 20 + 4 * i, v.wordBits[i]);
  put16(b.data() + 28, v.partBits);
  put16(b.data() + 30, v.count);
  std::memcpy(b.data() + 32, v.data.data(), 4096);
}
struct Context {
  FileDataEvent *value;
  int mode;
  int calls = 0;
  static bool write(void *p, BufferWriter &writer, const Event &event) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("write binding");
    return c.mode ? c.mode == 2 : FileDataEventClass().write(writer, *c.value);
  }
  static bool read(void *p, Event &event, BufferReader &reader) {
    auto &c = *static_cast<Context *>(p);
    ++c.calls;
    if (&event != &c.value->header)
      throw std::runtime_error("read binding");
    return c.mode ? c.mode == 2 : FileDataEventClass().read(*c.value, reader);
  }
};
static void integrations() {
  using namespace presonus::uc;
  const unsigned sizes[4] = {0, 1, 4095, 4096};
  const std::uint32_t ids[4] = {0, 32768, 0x12345678, 0xffffffff};
  for (unsigned variant = 0; variant < 4; ++variant) {
    FileDataEvent value;
    value.header = {17988, 0, 17, 29};
    value.idBits = ids[variant];
    value.wordBits = {0x7fc12345, 0x7f812345};
    value.partBits = static_cast<unsigned short>(32768 + variant);
    value.count = static_cast<unsigned short>(sizes[variant]);
    for (unsigned i = 0; i < 4096; ++i)
      value.data[i] = static_cast<unsigned char>(i * 29 + variant * 71);
    FileDataFactoryCodec adapter;
    adapter.bind(value);
    FactoryRegistry registry;
    adapter.registerIn(registry);
    EventFactory factory(registry);
    std::array<char, 8192> wire{};
    int size = factory.write(wire.data(), 8192, value.header);
    if (size != 20 + int(value.count))
      throw std::runtime_error("FileData encode length");
    BufferReader reader(wire.data(), size);
    auto *item =
        dynamic_cast<TypedEventItem<FileDataEvent> *>(factory.read(reader));
    if (!item || reader.position() != size ||
        item->value.header.type != 17988 || item->value.header.routeA != 17 ||
        item->value.header.routeB != 29 ||
        item->value.idBits != (value.idBits & 65535) ||
        item->value.wordBits != value.wordBits ||
        item->value.partBits != value.partBits ||
        item->value.count != value.count ||
        std::memcmp(item->value.data.data(), value.data.data(), value.count))
      throw std::runtime_error("FileData decode fields/rawbytes");
    std::array<char, 8192> rewritten{};
    if (factory.create(item->getData()) != nullptr ||
        factory.write(rewritten.data(), 8192, item->getData()) != 6)
      throw std::runtime_error("FileData returned binding");
    adapter.bind(item->value);
    rewritten.fill(0);
    if (factory.write(rewritten.data(), 8192, item->getData()) != size ||
        rewritten != wire)
      throw std::runtime_error("FileData read-bind-write");
    auto *clone = dynamic_cast<TypedEventItem<FileDataEvent> *>(
        factory.create(item->getData()));
    if (!clone)
      throw std::runtime_error("FileData clone");
    adapter.bind(clone->value);
    rewritten.fill(0);
    if (factory.write(rewritten.data(), 8192, clone->getData()) != size ||
        rewritten != wire)
      throw std::runtime_error("FileData clone data");
    adapter.unbind(clone->value);
    delete clone;
    adapter.unbind(item->value);
    delete item;
    BufferReader truncated(wire.data(), size - 1);
    if (factory.read(truncated) != nullptr ||
        truncated.position() != (value.count ? 20 : 18))
      throw std::runtime_error("FileData strict data/count truncation");
    if (value.count == 4096) {
      auto over = wire;
      over[18] = 1;
      over[19] = 16;
      over[size] = char(0xa5);
      BufferReader complete(over.data(), size + 1);
      auto *capped =
          dynamic_cast<TypedEventItem<FileDataEvent> *>(factory.read(complete));
      if (!capped || complete.position() != size + 1 ||
          capped->value.count != 4097 ||
          std::memcmp(capped->value.data.data(), value.data.data(), 4096))
        throw std::runtime_error("FileData capped read and skip");
      delete capped;
      BufferReader failedSkip(over.data(), size);
      if (factory.read(failedSkip) != nullptr || failedSkip.position() != size)
        throw std::runtime_error("FileData retained prefix on skip failure");
      value.count = 4097;
      if (factory.write(rewritten.data(), 4096, value.header) != 20)
        throw std::runtime_error("FileData oversized pre-copy rejection");
      value.count = 4096;
    }
    auto *blank = dynamic_cast<TypedEventItem<FileDataEvent> *>(
        factory.createType(17988));
    if (!blank)
      throw std::runtime_error("FileData createType");
    adapter.bind(blank->value);
    auto *copy = dynamic_cast<TypedEventItem<FileDataEvent> *>(
        factory.create(blank->getData()));
    if (!copy)
      throw std::runtime_error("FileData blank clone");
    adapter.bind(copy->value);
    if (factory.write(rewritten.data(), 8192, copy->getData()) != 20)
      throw std::runtime_error("FileData blank write");
    adapter.unbind(copy->value);
    delete copy;
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
  if (std::memcmp(magic, "UCFDv001", 8))
    return 3;
  auto count = word(in);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[24];
    read(in, meta, 24);
    auto op = meta[1], mode = meta[3];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12), size = get32(meta + 16),
         seed = get32(meta + 20);
    if (size < capacity || size > 65587 || offset > capacity || op > 3 ||
        mode > 2)
      throw std::runtime_error("invalid FileData metadata");
    std::vector<unsigned char> io(size);
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
    FileDataEvent value;
    load(value, event);
    Context context{&value, int(mode)};
    PrimitiveEventClass<FileDataEvent, 17988> dispatch(
        {&context, Context::write, Context::read});
    bool result = op < 2 ? (op % 2 ? FileDataEventClass().read(value, reader)
                                   : FileDataEventClass().write(writer, value))
                         : (op % 2 ? dispatch.read(value.header, reader)
                                   : dispatch.write(writer, value.header));
    if (op >= 2 &&
        context.calls != (capacity - offset >= (op % 2 ? 4 : 6) ? 1 : 0))
      throw std::runtime_error("FileData payload call count");
    save(event, value);
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
  std::cout
      << count
      << " original ARM fixed FileData fixtures passed\n4 composed FileData "
         "routing/raw-bits/clone/create/binding/cap-copy-skip groups passed\n";
}
