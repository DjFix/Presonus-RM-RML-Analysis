#include "presonus/uc/typed_factory_codec.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace Presonus::UC;
using Image = std::array<unsigned char, 512>;
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
static Event header(const Image &b) {
  return {get32(b.data()), get32(b.data() + 4), get32(b.data() + 8),
          get32(b.data() + 12)};
}
static void saveHeader(Image &b, const Event &e) {
  put32(b.data(), e.type);
  put32(b.data() + 4, e.reserved04);
  put32(b.data() + 8, e.routeA);
  put32(b.data() + 12, e.routeB);
}
static void load(UDPMappingEvent &e, const Image &b) {
  e.header = header(b);
  e.mapping = get16(b.data() + 16);
}
static void save(Image &b, const UDPMappingEvent &e) {
  saveHeader(b, e.header);
  put16(b.data() + 16, e.mapping);
}
static void load(MidiMessageEvent &e, const Image &b) {
  e.header = header(b);
  std::memcpy(e.bytes.data(), b.data() + 16, 4);
}
static void save(Image &b, const MidiMessageEvent &e) {
  saveHeader(b, e.header);
  std::memcpy(b.data() + 16, e.bytes.data(), 4);
}
static void load(ExtensionQueryEvent &e, const Image &b) {
  e.header = header(b);
  e.query = get32(b.data() + 16);
}
static void save(Image &b, const ExtensionQueryEvent &e) {
  saveHeader(b, e.header);
  put32(b.data() + 16, e.query);
}
static void load(ParamValueEvent &e, const Image &b) {
  e.header = header(b);
  std::memcpy(e.path.data(), b.data() + 16, 128);
  e.index = get16(b.data() + 144);
  std::memcpy(e.reserved92.data(), b.data() + 146, 2);
  e.valueBits = get32(b.data() + 148);
}
static void save(Image &b, const ParamValueEvent &e) {
  saveHeader(b, e.header);
  std::memcpy(b.data() + 16, e.path.data(), 128);
  put16(b.data() + 144, e.index);
  std::memcpy(b.data() + 146, e.reserved92.data(), 2);
  put32(b.data() + 148, e.valueBits);
}
static void load(ParamStringEvent &e, const Image &b) {
  e.header = header(b);
  std::memcpy(e.path.data(), b.data() + 16, 128);
  e.index = get16(b.data() + 144);
  std::memcpy(e.text.data(), b.data() + 146, 256);
}
static void save(Image &b, const ParamStringEvent &e) {
  saveHeader(b, e.header);
  std::memcpy(b.data() + 16, e.path.data(), 128);
  put16(b.data() + 144, e.index);
  std::memcpy(b.data() + 146, e.text.data(), 256);
}
static void load(DiscoveryAliveEvent &e, const Image &b) {
  e.header = header(b);
  e.versionBits = get32(b.data() + 16);
  e.extensionBits = get32(b.data() + 20);
  e.extensionA = get16(b.data() + 24);
  e.extensionB = get16(b.data() + 26);
  std::memcpy(e.extensionBytes.data(), b.data() + 28, 8);
  for (int i = 0; i < 4; ++i)
    std::memcpy(e.strings[i].data(), b.data() + 36 + 64 * i, 64);
}
static void save(Image &b, const DiscoveryAliveEvent &e) {
  saveHeader(b, e.header);
  put32(b.data() + 16, e.versionBits);
  put32(b.data() + 20, e.extensionBits);
  put16(b.data() + 24, e.extensionA);
  put16(b.data() + 26, e.extensionB);
  std::memcpy(b.data() + 28, e.extensionBytes.data(), 8);
  for (int i = 0; i < 4; ++i)
    std::memcpy(b.data() + 36 + 64 * i, e.strings[i].data(), 64);
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
bool execute(Image &event, BufferWriter &writer, BufferReader &reader,
             bool isRead, int mode, int expectedCalls,
             bool payloadOnly = false) {
  T value;
  load(value, event);
  Context<T, Codec> context{&value, mode};
  PrimitiveEventClass<T, Type> dispatch(
      {&context, Context<T, Codec>::write, Context<T, Codec>::read});
  bool result = payloadOnly ? (isRead ? Codec().read(value, reader)
                                      : Codec().write(writer, value))
                            : (isRead ? dispatch.read(value.header, reader)
                                      : dispatch.write(writer, value.header));
  if (!payloadOnly && context.calls != expectedCalls)
    throw std::runtime_error("typed virtual callback count");
  save(event, value);
  return result;
}
template <class T, class Codec, int Type> void roundtrip(T value) {
  using namespace presonus::uc;
  value.header = {Type, 0, 17, 29};
  TypedFactoryCodec<T, Codec, Type> adapter;
  adapter.bind(value);
  FactoryRegistry registry;
  adapter.registerIn(registry);
  EventFactory factory(registry);
  std::array<char, 512> data{};
  int size = factory.write(data.data(), 512, value.header);
  if (size < 6)
    throw std::runtime_error("adapter encode");
  auto *item =
      dynamic_cast<TypedEventItem<T> *>(factory.read(data.data(), size));
  if (!item || item->value.header.type != Type ||
      item->value.header.routeA != 17 || item->value.header.routeB != 29)
    throw std::runtime_error("adapter decode");
  std::array<unsigned char, 512> a{}, b{};
  BufferWriter aw(a.data(), 512), bw(b.data(), 512);
  if (!Codec().write(aw, value) || !Codec().write(bw, item->value) ||
      aw.position() != bw.position() || a != b)
    throw std::runtime_error("adapter payload mismatch");
  std::array<char, 512> rewritten{};
  if (factory.create(item->getData()) != nullptr ||
      factory.write(rewritten.data(), 512, item->getData()) != 6)
    throw std::runtime_error("unbound returned item contract");
  adapter.bind(item->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 512, item->getData()) != size ||
      std::memcmp(rewritten.data(), data.data(), std::size_t(size)))
    throw std::runtime_error("bound read to write");
  auto *readClone = factory.create(item->getData());
  if (!readClone)
    throw std::runtime_error("bound read to clone");
  delete readClone;
  adapter.unbind(item->value);
  delete item;
  auto *cloned =
      dynamic_cast<TypedEventItem<T> *>(factory.create(value.header));
  if (!cloned)
    throw std::runtime_error("adapter clone");
  a.fill(0);
  b.fill(0);
  BufferWriter cw(a.data(), 512), dw(b.data(), 512);
  Codec().write(cw, value);
  Codec().write(dw, cloned->value);
  if (a != b || cw.position() != dw.position())
    throw std::runtime_error("adapter clone payload");
  delete cloned;
  auto *blank = dynamic_cast<TypedEventItem<T> *>(factory.createType(Type));
  if (!blank || blank->getData().type != Type)
    throw std::runtime_error("adapter createType");
  if (factory.create(blank->getData()) != nullptr)
    throw std::runtime_error("unbound createType item");
  adapter.bind(blank->value);
  auto *blankClone =
      dynamic_cast<TypedEventItem<T> *>(factory.create(blank->getData()));
  if (!blankClone)
    throw std::runtime_error("bound createType to clone");
  adapter.bind(blankClone->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 512, blankClone->getData()) < 6)
    throw std::runtime_error("bound createType clone write");
  adapter.unbind(blankClone->value);
  delete blankClone;
  adapter.unbind(blank->value);
  delete blank;
  if (factory.read(data.data(), size - 1) != nullptr)
    throw std::runtime_error("adapter truncation");
  adapter.unbind(value);
  if (factory.create(value.header) != nullptr)
    throw std::runtime_error("adapter unbind");
}
static void adapters() {
  UDPMappingEvent udp;
  udp.mapping = 65535;
  roundtrip<UDPMappingEvent, UDPMappingEventClass, 21837>(udp);
  MidiMessageEvent midi;
  midi.bytes = {0, 0x90, 0x80, 0xff};
  roundtrip<MidiMessageEvent, MidiMessageEventClass, 19789>(midi);
  ExtensionQueryEvent ext;
  ext.query = 0x80ff0011;
  roundtrip<ExtensionQueryEvent, ExtensionQueryEventClass, 17745>(ext);
  ParamValueEvent value;
  std::memcpy(value.path.data(), "gain", 5);
  value.index = 65535;
  value.valueBits = 0x7f812345;
  roundtrip<ParamValueEvent, ParamValueEventClass, 20566>(value);
  ParamStringEvent text;
  std::memcpy(text.path.data(), "name", 5);
  text.index = 32768;
  text.text = {char(0xff), char(0x80), 'x', 0};
  roundtrip<ParamStringEvent, ParamStringEventClass, 20563>(text);
  DiscoveryAliveEvent discovery;
  discovery.versionBits = 0x80000001;
  discovery.extensionBits = 0x80ffffff;
  discovery.extensionA = 65535;
  discovery.extensionB = 32768;
  discovery.extensionBytes = {0, 1, 0x80, 0xff, 0x31, 0, 0x7f, 0x90};
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < i * 17; ++j)
      discovery.strings[i][j] = char(0x80 + j);
  roundtrip<DiscoveryAliveEvent, DiscoveryAliveEventClass, 17473>(discovery);
}
static void read(std::istream &in, void *p, std::size_t n) {
  if (!in.read(static_cast<char *>(p), static_cast<std::streamsize>(n)))
    throw std::runtime_error("truncated fixture");
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCDSv001", 8))
    return 3;
  unsigned char countbytes[4];
  read(in, countbytes, 4);
  auto count = get32(countbytes);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[16];
    read(in, meta, 16);
    auto op = meta[1];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12);
    Image io, event, expectedIo, expectedEvent;
    read(in, io.data(), 512);
    read(in, event.data(), 512);
    read(in, expectedIo.data(), 512);
    read(in, expectedEvent.data(), 512);
    BufferReader reader(io.data(), int(capacity), int(offset));
    BufferWriter writer(io.data(), int(capacity), int(offset));
    bool result = false;
    int calls = capacity - offset >= (op % 2 ? 4 : 6) ? 1 : 0;
    switch (op / 2) {
    case 0:
      result = execute<UDPMappingEvent, UDPMappingEventClass, 21837>(
          event, writer, reader, op % 2, meta[3], calls);
      break;
    case 1:
      result = execute<MidiMessageEvent, MidiMessageEventClass, 19789>(
          event, writer, reader, op % 2, meta[3], calls);
      break;
    case 2:
      result = execute<ExtensionQueryEvent, ExtensionQueryEventClass, 17745>(
          event, writer, reader, op % 2, meta[3], calls);
      break;
    case 3:
      result = execute<ParamValueEvent, ParamValueEventClass, 20566>(
          event, writer, reader, op % 2, meta[3], calls);
      break;
    case 4:
      result = execute<ParamStringEvent, ParamStringEventClass, 20563>(
          event, writer, reader, op % 2, meta[3], calls);
      break;
    case 5:
    case 6:
      result = execute<DiscoveryAliveEvent, DiscoveryAliveEventClass, 17473>(
          event, writer, reader, op % 2, meta[3], calls, op >= 12);
      break;
    default:
      return 4;
    }
    auto cursor = op % 2 ? reader.position() : writer.position();
    if (result != bool(meta[2]) || cursor != int(next) || io != expectedIo ||
        event != expectedEvent) {
      std::cerr << "mismatch row=" << row << " role=" << unsigned(meta[0])
                << " op=" << unsigned(op) << " mode=" << unsigned(meta[3])
                << " capacity=" << capacity << " offset=" << offset
                << " result=" << result << '/' << unsigned(meta[2])
                << " cursor=" << cursor << '/' << next
                << " io=" << (io == expectedIo)
                << " event=" << (event == expectedEvent) << '\n';
      return 1;
    }
  }
  if (in.peek() != std::char_traits<char>::eof())
    return 5;
  adapters();
  std::cout
      << count
      << " original ARM dispatch fixtures passed\n6 typed factory adapters "
         "passed routing/clone/create/truncation/binding checks\n";
}
