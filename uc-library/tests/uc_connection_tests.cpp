#include "connection_fixture.hpp"
#include "presonus/uc/connection.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>
using namespace Presonus::UC;
static constexpr std::array<std::uint32_t, 8> palette = {
    0,           1,     0xffffffffu, 0x80000000u,
    0x7fffffffu, 19537, 0x12345678u, 0x87654321u};
static std::uint32_t word(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static int signedBits(std::uint32_t x) {
  int v;
  static_assert(sizeof(v) == 4);
  std::memcpy(&v, &x, 4);
  return v;
}
struct Context {
  int granularity;
  std::uint32_t sendResult;
  unsigned granCalls = 0, sendCalls = 0;
  std::array<std::uint32_t, 2> payload;
  std::array<std::uint32_t, 6> reply{};
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "UCCNv001", 8))
    return 3;
  unsigned records = word(header.data() + 8);
  for (unsigned index = 0; index < records; ++index) {
    std::array<unsigned char, 80> raw{};
    f.read(reinterpret_cast<char *>(raw.data()), raw.size());
    if (!f)
      return 4;
    std::array<std::uint32_t, 20> v{};
    for (unsigned i = 0; i < v.size(); ++i)
      v[i] = word(raw.data() + 4 * i);
    unsigned op = v[0], arg = v[1], n = v[2], seed = v[3];
    if (n > 8 || op > 6)
      return 5;
    std::array<unsigned, 8> identities{};
    std::array<presonus::uc::ConnectionSenderView, 8> entries{};
    for (unsigned i = 0; i < 8; ++i)
      entries[i] = {&identities[i], palette[(seed + i) % 8],
                    palette[(seed + 2 * i) % 8]};
    Context context{signedBits(arg), arg & 1, 0, 0, {v[8], v[9]}, {}};
    presonus::uc::ConnectionState state;
    state.senders = entries.data();
    state.senderCount = n;
    state.channelLimitBits = v[4];
    state.context = &context;
    state.granularity = [](void *p) {
      auto &c = *static_cast<Context *>(p);
      ++c.granCalls;
      return c.granularity;
    };
    state.queryPayload = [](void *p, const Event &) {
      return static_cast<Context *>(p)->payload;
    };
    state.sendReply = [](void *p, const presonus::uc::ConnectionReplyView &r) {
      auto &c = *static_cast<Context *>(p);
      ++c.sendCalls;
      c.reply = {r.header.type,   r.header.reserved04, r.header.routeA,
                 r.header.routeB, r.payloadWords[0],   r.payloadWords[1]};
      return bool(c.sendResult);
    };
    hierarchy_test::ConcreteConnection connection(state);
    Event event{v[5], 0x12345678u, v[6], v[7]};
    const Event before = event;
    std::uint32_t result = 0;
    void *found = nullptr;
    switch (op) {
    case 0:
      connection.adjustRouting(event, arg & 1);
      break;
    case 1:
      result = connection.sendPeriodicEvent(event);
      break;
    case 2:
      result = connection.reset();
      break;
    case 3:
      found = connection.findSender(signedBits(arg));
      break;
    case 4:
      found = connection.findSenderWithLocalID(signedBits(arg));
      break;
    case 5:
      connection.initChannel();
      break;
    case 6:
      result = connection.handleInternal(event);
      break;
    }
    if (op == 3 || op == 4) {
      result = 0xffffffffu;
      for (unsigned i = 0; i < n; ++i)
        if (found == &identities[i]) {
          result = i;
          break;
        }
      if (found && result == 0xffffffffu)
        return 6;
    }
    std::array<std::uint32_t, 10> actual = {result,
                                            state.channelLimitBits,
                                            context.granCalls,
                                            context.sendCalls,
                                            context.reply[0],
                                            context.reply[1],
                                            context.reply[2],
                                            context.reply[3],
                                            context.reply[4],
                                            context.reply[5]};
    for (unsigned i = 0; i < actual.size(); ++i)
      if (actual[i] != v[10 + i]) {
        std::fprintf(stderr, "fixture%u op%u word%u got%08x want%08x\n", index,
                     op, i, actual[i], v[10 + i]);
        return 7;
      }
    if (std::memcmp(&before, &event, sizeof(event)) || state.senderCount != n ||
        state.senders != entries.data())
      return 8;
    for (unsigned i = 0; i < 8; ++i)
      if (entries[i].identity != &identities[i] ||
          entries[i].remoteBits != palette[(seed + i) % 8] ||
          entries[i].localBits != palette[(seed + 2 * i) % 8])
        return 9;
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 10;
  std::printf("%u original ARM Connection fixtures passed\n", records);
}
