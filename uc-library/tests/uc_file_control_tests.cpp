#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/no_member_events.hpp"
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
template <class T> static void loadPayload(T &, const Image &) {}
template <class T> static void savePayload(Image &, const T &) {}
static void loadPayload(FileRequestEvent &v, const Image &b) {
  v.idBits = get32(b.data() + 16);
  v.requestBits = get32(b.data() + 20);
  for (int i = 0; i < 2; ++i)
    std::memcpy(v.strings[i].data(), b.data() + 24 + 256 * i, 256);
}
static void savePayload(Image &b, const FileRequestEvent &v) {
  put32(b.data() + 16, v.idBits);
  put32(b.data() + 20, v.requestBits);
  for (int i = 0; i < 2; ++i)
    std::memcpy(b.data() + 24 + 256 * i, v.strings[i].data(), 256);
}
static void loadPayload(FileDataRateEvent &v, const Image &b) {
  v.idBits = get32(b.data() + 16);
  for (int i = 0; i < 3; ++i)
    v.wordBits[i] = get32(b.data() + 20 + 4 * i);
}
static void savePayload(Image &b, const FileDataRateEvent &v) {
  put32(b.data() + 16, v.idBits);
  for (int i = 0; i < 3; ++i)
    put32(b.data() + 20 + 4 * i, v.wordBits[i]);
}
static void loadPayload(FileAbortEvent &v, const Image &b) {
  v.idBits = get32(b.data() + 16);
}
static void savePayload(Image &b, const FileAbortEvent &v) {
  put32(b.data() + 16, v.idBits);
}
template <class T> static void load(T &v, const Image &b) {
  v.header = {get32(b.data()), get32(b.data() + 4), get32(b.data() + 8),
              get32(b.data() + 12)};
  loadPayload(v, b);
}
template <class T> static void save(Image &b, const T &v) {
  put32(b.data(), v.header.type);
  put32(b.data() + 4, v.header.reserved04);
  put32(b.data() + 8, v.header.routeA);
  put32(b.data() + 12, v.header.routeB);
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
  bool result = op < 14 ? (op % 2 ? Codec().read(value, reader)
                                  : Codec().write(writer, value))
                        : (op % 2 ? dispatch.read(value.header, reader)
                                  : dispatch.write(writer, value.header));
  if (op >= 14 && context.calls != expectedCalls)
    throw std::runtime_error("wire virtual callback count");
  save(b, value);
  return result;
}
template <class T> static void validate(const T &, const T &) {}
static void validate(const FileRequestEvent &input,
                     const FileRequestEvent &output) {
  if (output.idBits != (input.idBits & 65535) ||
      output.requestBits != input.requestBits)
    throw std::runtime_error("request id/endian");
}
static void validate(const FileDataRateEvent &input,
                     const FileDataRateEvent &output) {
  if (output.idBits != (input.idBits & 65535) ||
      output.wordBits != input.wordBits)
    throw std::runtime_error("rate id/raw bits");
}
static void validate(const FileAbortEvent &input,
                     const FileAbortEvent &output) {
  if (output.idBits != (input.idBits & 65535))
    throw std::runtime_error("abort id zeroextend");
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
    throw std::runtime_error("wire encode");
  BufferReader reader(wire.data(), size);
  auto *item = dynamic_cast<TypedEventItem<T> *>(factory.read(reader));
  if (!item || reader.position() != size || item->value.header.type != Type ||
      item->value.header.routeA != 17 || item->value.header.routeB != 29)
    throw std::runtime_error("wire decode");
  validate(value, item->value);
  std::array<unsigned char, 2048> expected{}, actual{};
  BufferWriter ew(expected.data(), 2048), aw(actual.data(), 2048);
  if (!Codec().write(ew, value) || !Codec().write(aw, item->value) ||
      ew.position() != aw.position() || expected != actual)
    throw std::runtime_error("wire payload roundtrip");
  std::array<char, 2048> rewritten{};
  if (factory.create(item->getData()) != nullptr ||
      factory.write(rewritten.data(), 2048, item->getData()) != 6)
    throw std::runtime_error("returned wire binding");
  adapter.bind(item->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, item->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("bound wire read write");
  auto *clone =
      dynamic_cast<TypedEventItem<T> *>(factory.create(item->getData()));
  if (!clone)
    throw std::runtime_error("bound wire clone");
  adapter.bind(clone->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, clone->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("wire clone payload");
  adapter.unbind(clone->value);
  delete clone;
  adapter.unbind(item->value);
  delete item;
  BufferReader truncated(wire.data(), size - 1);
  if (factory.read(truncated) != nullptr)
    throw std::runtime_error("wire truncation accepted");
  auto *blank = dynamic_cast<TypedEventItem<T> *>(factory.createType(Type));
  if (!blank)
    throw std::runtime_error("wire createType");
  adapter.bind(blank->value);
  auto *copy =
      dynamic_cast<TypedEventItem<T> *>(factory.create(blank->getData()));
  if (!copy)
    throw std::runtime_error("wire blank clone");
  adapter.bind(copy->value);
  if (factory.write(rewritten.data(), 2048, copy->getData()) < 6)
    throw std::runtime_error("wire blank write");
  adapter.unbind(copy->value);
  delete copy;
  adapter.unbind(blank->value);
  delete blank;
  adapter.unbind(value);
}
static void integrations() {
  integration<NoOpEvent, PrimitiveEventClassNoMembers<NoOpEvent, 20047>, 20047>(
      {});
  integration<DiscoveryLeaveEvent,
              PrimitiveEventClassNoMembers<DiscoveryLeaveEvent, 17484>, 17484>(
      {});
  integration<DiscoveryQueryEvent,
              PrimitiveEventClassNoMembers<DiscoveryQueryEvent, 17489>, 17489>(
      {});
  integration<KeepAliveEvent,
              PrimitiveEventClassNoMembers<KeepAliveEvent, 19265>, 19265>({});
  const std::uint32_t ids[4] = {0, 32768, 0x12345678, 0xffffffff};
  const std::uint32_t bits[8] = {0,          0x80000000, 0x7f800000, 0xff800000,
                                 0x7fc12345, 0x7f812345, 0xffffffff, 1};
  for (unsigned variant = 0; variant < 4; ++variant) {
    FileRequestEvent request;
    request.idBits = ids[variant];
    request.requestBits = bits[variant + 3];
    unsigned n[4] = {0, 1, 31, 255};
    for (unsigned j = 0; j < 2; ++j) {
      for (unsigned i = 0; i < n[(variant + j) % 4]; ++i)
        request.strings[j][i] = char((i * 29 + 17) % 255 + 1);
      request.strings[j][n[(variant + j) % 4]] = 0;
    }
    integration<FileRequestEvent, FileRequestEventClass, 18002>(request);
    FileDataRateEvent rate;
    rate.idBits = ids[variant];
    for (unsigned i = 0; i < 3; ++i)
      rate.wordBits[i] = bits[(variant + i + 3) % 8];
    integration<FileDataRateEvent, FileDataRateEventClass, 18003>(rate);
    FileAbortEvent abort;
    abort.idBits = ids[variant];
    integration<FileAbortEvent, FileAbortEventClass, 17985>(abort);
  }
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCFWv001", 8))
    return 3;
  auto count = word(in);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[24];
    read(in, meta, 24);
    auto op = meta[1], mode = meta[3];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12), size = get32(meta + 16),
         seed = get32(meta + 20);
    if (size < capacity || size > 2071 || offset > capacity || op > 27 ||
        mode > 2)
      throw std::runtime_error("invalid wire metadata");
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
    auto beforeIo = io;
    auto beforeEvent = event;
    BufferReader reader(io.data(), int(capacity), int(offset));
    BufferWriter writer(io.data(), int(capacity), int(offset));
    int calls = capacity - offset >= (op % 2 ? 4 : 6) ? 1 : 0;
    bool result = false;
    switch ((op % 14) / 2) {
    case 0:
      result =
          execute<NoOpEvent, PrimitiveEventClassNoMembers<NoOpEvent, 20047>,
                  20047>(event, reader, writer, op, mode, calls);
      break;
    case 1:
      result = execute<DiscoveryLeaveEvent,
                       PrimitiveEventClassNoMembers<DiscoveryLeaveEvent, 17484>,
                       17484>(event, reader, writer, op, mode, calls);
      break;
    case 2:
      result = execute<DiscoveryQueryEvent,
                       PrimitiveEventClassNoMembers<DiscoveryQueryEvent, 17489>,
                       17489>(event, reader, writer, op, mode, calls);
      break;
    case 3:
      result =
          execute<KeepAliveEvent,
                  PrimitiveEventClassNoMembers<KeepAliveEvent, 19265>, 19265>(
              event, reader, writer, op, mode, calls);
      break;
    case 4:
      result = execute<FileRequestEvent, FileRequestEventClass, 18002>(
          event, reader, writer, op, mode, calls);
      break;
    case 5:
      result = execute<FileDataRateEvent, FileDataRateEventClass, 18003>(
          event, reader, writer, op, mode, calls);
      break;
    case 6:
      result = execute<FileAbortEvent, FileAbortEventClass, 17985>(
          event, reader, writer, op, mode, calls);
      break;
    default:
      return 4;
    }
    int cursor = op % 2 ? reader.position() : writer.position();
    if (op < 8 && (!result || cursor != int(offset) || io != beforeIo ||
                   event != beforeEvent))
      throw std::runtime_error("no-member payload state mutation");
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
      << " original ARM no-member/file-control fixtures passed\n16 composed "
         "header-only/file-control "
         "routing/id/raw-bit/clone/create/binding/truncation cases passed\n";
}
