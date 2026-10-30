#include "presonus/uc/misc_events.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <type_traits>
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
static void loadPayload(TimeCodeEvent &v, const Image &b) {
  v.keyBits = get32(b.data() + 16);
  v.recordCount = b[20];
  std::memcpy(v.reserved15.data(), b.data() + 21, 3);
  for (int i = 0; i < 4; ++i) {
    v.records[i].a = b[24 + 16 * i];
    v.records[i].b = b[25 + 16 * i];
    std::memcpy(v.records[i].reserved.data(), b.data() + 26 + 16 * i, 6);
    std::memcpy(v.records[i].rawBytes.data(), b.data() + 32 + 16 * i, 8);
  }
}
static void savePayload(Image &b, const TimeCodeEvent &v) {
  put32(b.data() + 16, v.keyBits);
  b[20] = v.recordCount;
  std::memcpy(b.data() + 21, v.reserved15.data(), 3);
  for (int i = 0; i < 4; ++i) {
    b[24 + 16 * i] = v.records[i].a;
    b[25 + 16 * i] = v.records[i].b;
    std::memcpy(b.data() + 26 + 16 * i, v.records[i].reserved.data(), 6);
    std::memcpy(b.data() + 32 + 16 * i, v.records[i].rawBytes.data(), 8);
  }
}
static void loadPayload(MusicInputEvent &v, const Image &b) {
  v.idBits = get32(b.data() + 16);
  v.modeByte = b[20];
  std::memcpy(v.reserved15.data(), b.data() + 21, 3);
  v.valueBits = get32(b.data() + 24);
}
static void savePayload(Image &b, const MusicInputEvent &v) {
  put32(b.data() + 16, v.idBits);
  b[20] = v.modeByte;
  std::memcpy(b.data() + 21, v.reserved15.data(), 3);
  put32(b.data() + 24, v.valueBits);
}
static void loadPayload(DebugEvent &v, const Image &b) {
  std::memcpy(v.text.data(), b.data() + 16, 1024);
}
static void savePayload(Image &b, const DebugEvent &v) {
  std::memcpy(b.data() + 16, v.text.data(), 1024);
}
static void loadPayload(MidiShortSysexEvent &v, const Image &b) {
  v.count = get16(b.data() + 16);
  std::memcpy(v.data.data(), b.data() + 18, 512);
}
static void savePayload(Image &b, const MidiShortSysexEvent &v) {
  put16(b.data() + 16, v.count);
  std::memcpy(b.data() + 18, v.data.data(), 512);
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
  bool result = op < 8 ? (op % 2 ? Codec().read(value, reader)
                                 : Codec().write(writer, value))
                       : (op % 2 ? dispatch.read(value.header, reader)
                                 : dispatch.write(writer, value.header));
  if (op >= 8 && context.calls != expectedCalls)
    throw std::runtime_error("misc virtual callback count");
  save(b, value);
  return result;
}
template <class T> static void validate(const T &, const T &) {}
static void validate(const TimeCodeEvent &in, const TimeCodeEvent &out) {
  if (out.keyBits != in.keyBits || out.recordCount != in.recordCount)
    throw std::runtime_error("timecode fields");
  for (unsigned i = 0; i < in.recordCount; ++i)
    if (in.records[i].a != out.records[i].a ||
        in.records[i].b != out.records[i].b ||
        in.records[i].rawBytes != out.records[i].rawBytes)
      throw std::runtime_error("timecode raw64 bytes");
}
static void validate(const MusicInputEvent &in, const MusicInputEvent &out) {
  if (out.idBits != (in.idBits & 65535) || out.modeByte != in.modeByte ||
      out.valueBits != in.valueBits)
    throw std::runtime_error("music mixed-width fields");
}
static void validate(const MidiShortSysexEvent &in,
                     const MidiShortSysexEvent &out) {
  if (out.count != in.count ||
      std::memcmp(in.data.data(), out.data.data(), in.count))
    throw std::runtime_error("short sysex byte data");
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
    throw std::runtime_error("misc encode");
  BufferReader reader(wire.data(), size);
  auto *item = dynamic_cast<TypedEventItem<T> *>(factory.read(reader));
  if (!item || reader.position() != size || item->value.header.type != Type ||
      item->value.header.routeA != 17 || item->value.header.routeB != 29)
    throw std::runtime_error("misc decode");
  validate(value, item->value);
  std::array<unsigned char, 2048> expected{}, actual{};
  BufferWriter ew(expected.data(), 2048), aw(actual.data(), 2048);
  if (!Codec().write(ew, value) || !Codec().write(aw, item->value) ||
      ew.position() != aw.position() || expected != actual)
    throw std::runtime_error("misc raw payload roundtrip");
  std::array<char, 2048> rewritten{};
  if (factory.create(item->getData()) != nullptr ||
      factory.write(rewritten.data(), 2048, item->getData()) != 6)
    throw std::runtime_error("misc returned binding");
  adapter.bind(item->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, item->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("misc bound read write");
  auto *copy =
      dynamic_cast<TypedEventItem<T> *>(factory.create(item->getData()));
  if (!copy)
    throw std::runtime_error("misc clone");
  adapter.bind(copy->value);
  rewritten.fill(0);
  if (factory.write(rewritten.data(), 2048, copy->getData()) != size ||
      rewritten != wire)
    throw std::runtime_error("misc clone bits");
  adapter.unbind(copy->value);
  delete copy;
  adapter.unbind(item->value);
  delete item;
  BufferReader truncated(wire.data(), size - 1);
  auto *partial = dynamic_cast<TypedEventItem<T> *>(factory.read(truncated));
  if constexpr (std::is_same_v<T, TimeCodeEvent>) {
    if (!partial || partial->value.recordCount != value.recordCount)
      throw std::runtime_error("timecode partial tail must be accepted");
    if (value.recordCount) {
      if (truncated.position() != size - 8 ||
          partial->value.records[value.recordCount - 1].rawBytes !=
              std::array<unsigned char, 8>{})
        throw std::runtime_error("timecode partial raw8");
    } else if (truncated.position() != size - 1)
      throw std::runtime_error("timecode missing count");
    delete partial;
    BufferReader shortPayload(wire.data(), 7);
    auto *shortItem =
        dynamic_cast<TypedEventItem<T> *>(factory.read(shortPayload));
    if (!shortItem || shortItem->value.keyBits != 0 ||
        shortItem->value.recordCount != 4 || shortPayload.position() != 7)
      throw std::runtime_error("timecode partial key/count continuation");
    delete shortItem;
    if (value.recordCount == 4) {
      auto extra = wire;
      extra[10] = char(255);
      extra[size] = char(0xf0);
      extra[size + 1] = char(0xff);
      BufferReader over(extra.data(), size + 2);
      auto *overItem = dynamic_cast<TypedEventItem<T> *>(factory.read(over));
      if (!overItem || overItem->value.recordCount != 4 ||
          over.position() != size)
        throw std::runtime_error("timecode clamp must not skip extras");
      delete overItem;
    }
  } else if (partial)
    throw std::runtime_error("misc strict payload truncation accepted");
  auto *blank = dynamic_cast<TypedEventItem<T> *>(factory.createType(Type));
  if (!blank)
    throw std::runtime_error("misc createType");
  adapter.bind(blank->value);
  auto *blankCopy =
      dynamic_cast<TypedEventItem<T> *>(factory.create(blank->getData()));
  if (!blankCopy)
    throw std::runtime_error("misc blank clone");
  adapter.bind(blankCopy->value);
  if (factory.write(rewritten.data(), 2048, blankCopy->getData()) < 6)
    throw std::runtime_error("misc blank write");
  adapter.unbind(blankCopy->value);
  delete blankCopy;
  adapter.unbind(blank->value);
  delete blank;
  adapter.unbind(value);
}
static void integrations() {
  const std::uint32_t ids[4] = {0, 0x80000000, 0x12345678, 0xffffffff};
  const std::uint32_t bits[4] = {0x80000000, 0x7f800000, 0x7fc12345,
                                 0x7f812345};
  unsigned counts[4] = {0, 1, 3, 4}, lengths[4] = {0, 1, 31, 1023},
           sysexCounts[4] = {0, 1, 511, 512};
  for (unsigned variant = 0; variant < 4; ++variant) {
    TimeCodeEvent time;
    time.keyBits = 0x80ff0011;
    time.recordCount = static_cast<unsigned char>(counts[variant]);
    for (unsigned i = 0; i < 4; ++i) {
      time.records[i].a = static_cast<unsigned char>(0x80 + i);
      time.records[i].b = static_cast<unsigned char>(0xff - i);
      for (unsigned j = 0; j < 8; ++j)
        time.records[i].rawBytes[j] =
            static_cast<unsigned char>(j * 29 + i * 17 + variant * 71);
    }
    integration<TimeCodeEvent, TimeCodeEventClass, 21571>(time);
    MusicInputEvent music;
    music.idBits = ids[variant];
    music.modeByte = static_cast<unsigned char>(0x80 + variant * 17);
    music.valueBits = bits[variant];
    integration<MusicInputEvent, MusicInputEventClass, 19785>(music);
    DebugEvent debug;
    for (unsigned i = 0; i < lengths[variant]; ++i)
      debug.text[i] = char((i * 29 + 17) % 255 + 1);
    debug.text[lengths[variant]] = 0;
    integration<DebugEvent, DebugEventClass, 17474>(debug);
    MidiShortSysexEvent sysex;
    sysex.count = static_cast<unsigned short>(sysexCounts[variant]);
    for (unsigned i = 0; i < 512; ++i)
      sysex.data[i] = static_cast<unsigned char>(i * 29 + variant * 71);
    integration<MidiShortSysexEvent, MidiShortSysexEventClass, 21331>(sysex);
  }
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCMIv001", 8))
    return 3;
  auto count = word(in);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[24];
    read(in, meta, 24);
    auto op = meta[1], mode = meta[3];
    auto capacity = get32(meta + 4), offset = get32(meta + 8),
         next = get32(meta + 12), size = get32(meta + 16),
         seed = get32(meta + 20);
    if (size < capacity || size > 65567 || offset > capacity || op > 15 ||
        mode > 2)
      throw std::runtime_error("invalid misc metadata");
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
    switch ((op % 8) / 2) {
    case 0:
      result = execute<TimeCodeEvent, TimeCodeEventClass, 21571>(
          event, reader, writer, op, mode, calls);
      break;
    case 1:
      result = execute<MusicInputEvent, MusicInputEventClass, 19785>(
          event, reader, writer, op, mode, calls);
      break;
    case 2:
      result = execute<DebugEvent, DebugEventClass, 17474>(
          event, reader, writer, op, mode, calls);
      break;
    case 3:
      result = execute<MidiShortSysexEvent, MidiShortSysexEventClass, 21331>(
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
            << " original ARM misc fixtures passed\n16 composed misc "
               "routing/raw-bit/clone/create/binding/partial-boundary groups "
               "passed\n";
}
