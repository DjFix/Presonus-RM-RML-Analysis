#include "presonus/uc/socket_channel.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <vector>
using namespace Presonus::UC;
static std::uint32_t word(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static std::uint32_t readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  if (!f)
    std::abort();
  return word(b.data());
}
static int signedBits(std::uint32_t x) {
  int v;
  static_assert(sizeof(v) == 4);
  std::memcpy(&v, &x, 4);
  return v;
}
using Row = std::array<std::uint32_t, 5>;
static int scripted(unsigned mode, unsigned index, int requested) {
  switch (mode) {
  case 0:
    return requested;
  case 1:
    return std::min(1, requested);
  case 2:
    return std::min(std::array<int, 3>{2, 3, 5}[index % 3], requested);
  case 3:
    return -1;
  case 4:
    return -37;
  case 5:
    return index == 0 ? std::min(1, requested) : -1;
  case 6:
    return std::array<int, 3>{0, std::min(2, requested),
                              -7}[std::min(index, 2u)];
  case 7:
    return index < 3 ? 0 : -11;
  case 8:
    return std::array<int, 4>{std::min(3, requested), 0, std::min(1, requested),
                              -2}[std::min(index, 3u)];
  case 9:
    return index % 3 != 2 ? 0 : std::min(2, requested);
  default:
    return index == 0 ? std::min(3, requested) : signedBits(0x80000000u);
  }
}
struct Context {
  unsigned char *io = nullptr;
  unsigned mode = 0, seed = 0, received = 0;
  std::uint32_t reply = 0, out = 0;
  bool mutate = false, bad = false;
  std::array<unsigned char, 128> sent{};
  std::vector<Row> trace;
  unsigned offset(const void *p) {
    if (!p)
      return 0xffffffffu;
    return static_cast<unsigned>(static_cast<const unsigned char *>(p) - io);
  }
};
static presonus::uc::SocketChannelIO bindings(Context &c) {
  return {
      &c,
      [](void *p, void *data, int count, int flags) {
        auto &c = *static_cast<Context *>(p);
        unsigned offset = c.offset(data);
        if (flags || count <= 0 || count > 64 || offset + unsigned(count) > 128)
          std::abort();
        int result = scripted(c.mode, c.trace.size(), count);
        if (result > 0) {
          for (int i = 0; i < result; ++i)
            static_cast<unsigned char *>(data)[i] = static_cast<unsigned char>(
                (c.received + unsigned(i)) * 11 + c.seed * 17);
          c.received += result;
        }
        c.trace.push_back({0, offset, unsigned(count), unsigned(flags),
                           std::uint32_t(result)});
        return result;
      },
      [](void *p, const void *data, int count, int flags) {
        auto &c = *static_cast<Context *>(p);
        unsigned offset = c.offset(data);
        int result = signedBits(c.reply);
        if (flags ||
            (count > 0 && (offset + unsigned(count) > 128 || result > count)))
          std::abort();
        if (result > 0)
          std::memcpy(c.sent.data(), data, result);
        c.trace.push_back(
            {1, offset, std::uint32_t(count), unsigned(flags), c.reply});
        return result;
      },
      [](void *p, int timeout) {
        auto &c = *static_cast<Context *>(p);
        c.trace.push_back({2, std::uint32_t(timeout), 0, 0, c.reply});
        return bool(c.reply);
      },
      [](void *p, int timeout) {
        auto &c = *static_cast<Context *>(p);
        c.trace.push_back({3, std::uint32_t(timeout), 0, 0, c.reply});
        return bool(c.reply);
      },
      [](void *p, int timeout) {
        auto &c = *static_cast<Context *>(p);
        c.trace.push_back({4, std::uint32_t(timeout), 0, 0, c.reply});
        return bool(c.reply);
      },
      [](void *p, int &out) {
        auto &c = *static_cast<Context *>(p);
        auto initial = std::uint32_t(out);
        if (initial)
          c.bad = true;
        if (c.mutate)
          out = signedBits(c.out);
        c.trace.push_back({5, initial, std::uint32_t(out), 0, c.reply});
        return signedBits(c.reply);
      }};
}
static void require(bool b) {
  if (!b) {
    std::fprintf(stderr, "composed codec/channel check failed\n");
    std::abort();
  }
}
struct Stream {
  std::vector<unsigned char> wire;
  unsigned cursor = 0, receiveCalls = 0, sendCalls = 0;
  int mode = 0, errorAfter = -1, sendReturn = 0x7fffffff;
};
static presonus::uc::SocketChannelIO streamBindings(Stream &s) {
  presonus::uc::SocketChannelIO io;
  io.context = &s;
  io.receive = [](void *p, void *out, int n, int flags) {
    auto &s = *static_cast<Stream *>(p);
    require(flags == 0 && n > 0);
    ++s.receiveCalls;
    if (s.errorAfter >= 0 && s.cursor >= unsigned(s.errorAfter))
      return -7;
    if (s.mode && s.receiveCalls % 3 != 0)
      return 0;
    int take = std::min<int>(n, s.wire.size() - s.cursor);
    if (s.mode)
      take = std::min(take, 2);
    if (s.errorAfter >= 0)
      take = std::min<int>(take, s.errorAfter - s.cursor);
    require(take > 0);
    std::memcpy(out, s.wire.data() + s.cursor, take);
    s.cursor += take;
    return take;
  };
  io.sendAll = [](void *p, const void *in, int n, int flags) {
    auto &s = *static_cast<Stream *>(p);
    require(flags == 0 && n > 0);
    ++s.sendCalls;
    int result = s.sendReturn == 0x7fffffff ? n : s.sendReturn;
    if (result > 0) {
      require(result <= n);
      auto *b = static_cast<const unsigned char *>(in);
      s.wire.assign(b, b + result);
    }
    return result;
  };
  return io;
}
static unsigned composed() {
  unsigned groups = 0;
  for (auto bits : {0u, 0x80000000u, 0x7fc00001u, 0xff800001u})
    for (int mode : {0, 1}) {
      presonus::uc::ParamValueFactoryCodec codec;
      presonus::uc::FactoryRegistry registry;
      codec.registerIn(registry);
      EventFactory factory(registry);
      ParamValueEvent event;
      event.header = {20566, 0, 0x1234, 0xabcd};
      std::strcpy(event.path.data(), "/transport/37");
      event.index = 65535;
      event.valueBits = bits;
      codec.bind(event);
      std::array<char, 128> encoded{}, readback{}, reencoded{};
      int length = factory.write(encoded.data(), encoded.size(), event.header);
      require(length > 0);
      Stream stream;
      stream.mode = mode;
      auto io = streamBindings(stream);
      SocketConnection::Channel channel(io);
      require(channel.write(encoded.data(), length) == length &&
              stream.sendCalls == 1);
      require(channel.read(readback.data(), length) == length &&
              std::memcmp(encoded.data(), readback.data(), length) == 0);
      std::unique_ptr<EventItem> item(factory.read(readback.data(), length));
      auto *typed =
          dynamic_cast<presonus::uc::TypedEventItem<ParamValueEvent> *>(
              item.get());
      require(typed && typed->value.valueBits == bits &&
              typed->value.index == 65535);
      codec.bind(typed->value);
      require(factory.write(reencoded.data(), reencoded.size(),
                            typed->value.header) == length &&
              std::memcmp(encoded.data(), reencoded.data(), length) == 0);
      codec.unbind(typed->value);
      codec.unbind(event);
      ++groups;
    }
  for (int errorAfter : {0, 3}) {
    presonus::uc::ParamValueFactoryCodec codec;
    presonus::uc::FactoryRegistry registry;
    codec.registerIn(registry);
    EventFactory factory(registry);
    ParamValueEvent event;
    event.header.type = 20566;
    event.path[0] = 0;
    codec.bind(event);
    std::array<char, 128> encoded{}, readback{};
    int length = factory.write(encoded.data(), encoded.size(), event.header);
    Stream stream;
    stream.errorAfter = errorAfter;
    auto io = streamBindings(stream);
    SocketConnection::Channel channel(io);
    require(channel.write(encoded.data(), length) == length);
    readback.fill(char(0xa5));
    require(channel.read(readback.data(), length) ==
            (errorAfter ? errorAfter : -7));
    require(std::memcmp(readback.data(), encoded.data(), errorAfter) == 0);
    for (unsigned i = errorAfter; i < readback.size(); ++i)
      require(static_cast<unsigned char>(readback[i]) == 0xa5);
    require(factory.read(readback.data(), errorAfter) == nullptr);
    codec.unbind(event);
    ++groups;
  }
  for (int status : {-5, 3}) {
    Stream stream;
    stream.sendReturn = status;
    auto io = streamBindings(stream);
    SocketConnection::Channel channel(io);
    const char data[] = "abcdef";
    require(channel.write(data, 6) == status && stream.sendCalls == 1);
    require(stream.wire.size() == (status < 0 ? 0u : unsigned(status)));
    ++groups;
  }
  return groups;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 8> magic{};
  f.read(reinterpret_cast<char *>(magic.data()), 8);
  if (std::memcmp(magic.data(), "UCCHv001", 8))
    return 3;
  unsigned records = readWord(f);
  for (unsigned index = 0; index < records; ++index) {
    std::array<unsigned, 8> in{};
    for (auto &v : in)
      v = readWord(f);
    unsigned expected = readWord(f), calls = readWord(f);
    if (in[0] > 6 || calls > 256)
      return 4;
    std::vector<Row> trace(calls);
    for (auto &row : trace)
      for (auto &v : row)
        v = readWord(f);
    std::array<unsigned char, 128> expectedIO{}, expectedSent{}, data{};
    f.read(reinterpret_cast<char *>(expectedIO.data()), 128);
    f.read(reinterpret_cast<char *>(expectedSent.data()), 128);
    if (!f)
      return 5;
    for (unsigned i = 0; i < data.size(); ++i)
      data[i] = static_cast<unsigned char>(29 * i + 71 * in[7]);
    Context c;
    c.io = data.data();
    c.mode = in[3];
    c.reply = in[4];
    c.out = in[5];
    c.mutate = in[6];
    c.seed = in[7];
    auto io = bindings(c);
    SocketConnection::Channel channel(io);
    void *buffer = in[2] == 0xffffffffu ? nullptr : data.data() + in[2];
    int result = 0, arg = signedBits(in[1]);
    switch (in[0]) {
    case 0:
      result = channel.read(buffer, arg);
      break;
    case 1:
      result = channel.write(buffer, arg);
      break;
    case 2:
      result = channel.isReadable(arg);
      break;
    case 3:
      result = channel.isWritable(arg);
      break;
    case 4:
      result = channel.hasErrors(arg);
      break;
    case 5:
      result = channel.getBytesAvailable();
      break;
    case 6:
      result = channel.getGranularity();
      break;
    }
    if (std::uint32_t(result) != expected || c.trace != trace ||
        data != expectedIO || c.sent != expectedSent || c.bad) {
      std::fprintf(stderr, "fixture%u op%u result/trace/bytes mismatch\n",
                   index, in[0]);
      return 6;
    }
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 7;
  unsigned groups = composed();
  require(groups == 12);
  std::printf("%u original ARM SocketChannel fixtures passed\n%u composed "
              "factory/channel chunking/error/raw-bits groups passed\n",
              records, groups);
}
