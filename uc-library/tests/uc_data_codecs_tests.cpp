#include "presonus/uc/data_codecs.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <type_traits>
#include <vector>
using namespace Presonus::UC;
static bool failAllocation;
static unsigned initialSize;
static std::array<unsigned, 5> trace;
extern "C" void *__real_core_realloc(void *, unsigned);
extern "C" void *__wrap_core_realloc(void *p, unsigned n) {
  if (failAllocation || n > 65536) {
    failAllocation = false;
    return nullptr;
  }
  void *q = __real_core_realloc(p, n);
  if (q && n > initialSize)
    std::memset(static_cast<unsigned char *>(q) + initialSize, 0xa5,
                n - initialSize);
  return q;
}
extern "C" bool __real__ZN4Core2IO6Buffer6resizeEj(void *, unsigned);
extern "C" bool __wrap__ZN4Core2IO6Buffer6resizeEj(void *p, unsigned n) {
  ++trace[2];
  return __real__ZN4Core2IO6Buffer6resizeEj(p, n);
}
extern "C" unsigned
__real__ZN4Core2IO6Buffer8copyFromEPKvj(void *, const void *, unsigned);
extern "C" unsigned
__wrap__ZN4Core2IO6Buffer8copyFromEPKvj(void *p, const void *s, unsigned n) {
  ++trace[3];
  return __real__ZN4Core2IO6Buffer8copyFromEPKvj(p, s, n);
}
template <class T> struct Item : presonus::uc::OwnedCodecItem<T> {
  using presonus::uc::OwnedCodecItem<T>::OwnedCodecItem;
  Event &getData() override {
    ++trace[0];
    return this->value.header;
  }
};
template <class T> struct Context {
  Item<T> &item;
  T &source;
  unsigned overrideHeader;
  presonus::uc::DataCodecBindings<T> bindings() {
    return {this,
            [](void *p, const Event &e) -> T & {
              auto &c = *static_cast<Context *>(p);
              if (&e == &c.item.value.header)
                return c.item.value;
              if (&e == &c.source.header)
                return c.source;
              std::abort();
            },
            [](void *p, EventItem &i) -> T & {
              auto &c = *static_cast<Context *>(p);
              if (&i != &c.item)
                std::abort();
              return c.item.value;
            },
            [](void *p, EventItem &i) -> Core::IO::Buffer & {
              auto &c = *static_cast<Context *>(p);
              if (&i != &c.item)
                std::abort();
              return c.item.storage;
            },
            [](void *p) -> EventItem * {
              ++trace[4];
              return &static_cast<Context *>(p)->item;
            },
            [](void *p, Event &e, BufferReader &r) {
              ++trace[1];
              unsigned mode = static_cast<Context *>(p)->overrideHeader;
              return mode == 0 ? EventClass{}.read(e, r) : mode == 2;
            }};
  }
};
static unsigned u32(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static void append(std::vector<unsigned char> &v, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    v.push_back(static_cast<unsigned char>(n >> (8 * i)));
}
static void word(std::array<unsigned char, 80> &io, unsigned &at, unsigned n,
                 bool big = false) {
  for (unsigned i = 0; i < 4; ++i)
    io[at++] = static_cast<unsigned char>(n >> (8 * (big ? 3 - i : i)));
}
template <class T, unsigned Kind>
static std::vector<unsigned char> run(const std::array<unsigned, 7> &args) {
  auto [op, count, cap, initial, borrowed, fail, overrideHeader] = args;
  std::array<unsigned char, 256> bytes;
  bytes.fill(0xa5);
  for (unsigned i = 0; i < 64; ++i)
    bytes[i] = static_cast<unsigned char>(i * 11);
  failAllocation = false;
  Item<T> item(initial ? bytes.data() + 64 : nullptr, initial, !borrowed);
  T source{};
  const unsigned type = Kind == 0 ? 21826 : Kind == 1 ? 16975 : 17227;
  item.value.header = {type, 0, 0xaabb, 0xccdd};
  item.value.data = bytes.data();
  item.value.sizeBits = 77;
  source.header = {type, 0, 0xaabb, 0xccdd};
  source.data = count < 0x80000000u ? bytes.data() : nullptr;
  source.sizeBits = count;
  if constexpr (Kind != 0) {
    item.value.word24 = 0xdeadbeef;
    source.word24 = 0x10203040;
  }
  if constexpr (Kind == 2) {
    item.value.word28 = 0x12345678;
    item.value.word32 = 0x87654321;
    source.word28 = 0x55667788;
    source.word32 = 0xa1b2c3d4;
  }
  Context<T> context{item, source, overrideHeader};
  std::array<unsigned char, 80> io;
  io.fill(0xcc);
  const bool read = op == 0 || op == 3 || op == 5 || op == 7;
  if (read) {
    unsigned at = 0;
    if (op != 7) {
      io[at++] = 0x11;
      io[at++] = 0;
      io[at++] = 0x22;
      io[at++] = 0;
    }
    if constexpr (Kind != 0)
      if (op != 7)
        word(io, at, source.word24, true);
    if constexpr (Kind == 2)
      if (op != 7) {
        word(io, at, source.word28);
        word(io, at, source.word32);
      }
    word(io, at, count);
    std::memcpy(io.data() + at, bytes.data(), 32);
  }
  trace.fill(0);
  initialSize = initial;
  failAllocation = fail;
  bool result = false;
  unsigned cursor = 0;
  if constexpr (Kind == 0) {
    DataEventClass<T, 21826> codec(context.bindings());
    if (op == 0) {
      BufferReader r(io.data(), cap);
      result = codec.read(item, r);
      cursor = r.position();
    } else if (op == 1) {
      BufferWriter w(io.data(), cap);
      result = codec.write(w, source.header);
      cursor = w.position();
    } else
      result = codec.create(source.header) == &item;
  } else if constexpr (Kind == 1) {
    BinaryEventClass codec(context.bindings());
    if (read) {
      BufferReader r(io.data(), cap);
      result = codec.read(item, r);
      cursor = r.position();
    } else {
      BufferWriter w(io.data(), cap);
      result = codec.write(w, source.header);
      cursor = w.position();
    }
  } else {
    MessageChunkEventClass codec(context.bindings());
    DataEventClass<T, 17227> data(context.bindings());
    if (read) {
      BufferReader r(io.data(), cap);
      result = op == 7 ? data.readDataBuffer(item, r) : codec.read(item, r);
      cursor = r.position();
    } else {
      BufferWriter w(io.data(), cap);
      result = op == 8 ? data.writeDataBuffer(w, source.header)
                       : codec.write(w, source.header);
      cursor = w.position();
    }
  }
  failAllocation = false;
  const T &value =
      (op == 1 || op == 4 || op == 6 || op == 8) ? source : item.value;
  const unsigned relation = value.data == nullptr                     ? 0
                            : value.data == item.storage.getAddress() ? 1
                                                                      : 2;
  std::vector<unsigned char> out;
  for (unsigned n :
       {unsigned(result), cursor, value.header.routeA, value.header.routeB,
        value.sizeBits, relation, item.storage.getSize()})
    append(out, n);
  if constexpr (Kind == 0) {
    append(out, 0);
    append(out, 0);
    append(out, 0);
  } else {
    append(out, value.word24);
    if constexpr (Kind == 2) {
      append(out, value.word28);
      append(out, value.word32);
    } else {
      append(out, 0);
      append(out, 0);
    }
  }
  for (unsigned n : trace)
    append(out, n);
  append(out, 0);
  std::array<unsigned char, 64> storage{};
  if (item.storage.getSize() > 64)
    std::abort();
  if (item.storage.getSize())
    std::memcpy(storage.data(), item.storage.getAddress(),
                item.storage.getSize());
  out.insert(out.end(), storage.begin(), storage.end());
  out.insert(out.end(), io.begin(), io.end());
  return out;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "UCDCv001", 8))
    return 3;
  unsigned records = u32(header.data() + 8);
  for (unsigned index = 0; index < records; ++index) {
    std::array<unsigned char, 28> raw{};
    std::array<unsigned char, 208> expected{};
    f.read(reinterpret_cast<char *>(raw.data()), raw.size());
    f.read(reinterpret_cast<char *>(expected.data()), expected.size());
    if (!f)
      return 4;
    std::array<unsigned, 7> args;
    for (unsigned i = 0; i < 7; ++i)
      args[i] = u32(raw.data() + 4 * i);
    auto actual = args[0] < 3   ? run<EncodedMessageEvent<21826>, 0>(args)
                  : args[0] < 5 ? run<BinaryEvent, 1>(args)
                                : run<MessageChunkEvent, 2>(args);
    if (actual.size() != expected.size() ||
        std::memcmp(actual.data(), expected.data(), expected.size())) {
      unsigned at = 0;
      while (at < expected.size() && actual[at] == expected[at])
        ++at;
      std::fprintf(stderr,
                   "fixture%u op%u count%u cap%u initial%u borrowed%u fail%u "
                   "override%u byte%u got%u want%u\n",
                   index, args[0], args[1], args[2], args[3], args[4], args[5],
                   args[6], at, actual[at], expected[at]);
      return 5;
    }
  }
  std::printf("%u original ARM UC codec cases passed using actual CCL Buffer; "
              "Core bodies not emulated\n",
              records);
}
