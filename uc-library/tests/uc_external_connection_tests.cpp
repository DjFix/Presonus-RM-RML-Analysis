#include "connection_fixture.hpp"
#include "presonus/uc/external_connection.hpp"
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
using namespace Presonus::UC;
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
  unsigned handlerCalls = 0, sendCalls = 0;
  std::uint32_t handlerResult = 0, sendResult = 0;
  std::array<std::uint32_t, 2> payload;
  std::array<std::uint32_t, 6> reply{};
  Event snapshot{};
  bool invalidOrigin = false;
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "UCEXv001", 8))
    return 3;
  unsigned records = word(header.data() + 8);
  for (unsigned index = 0; index < records; ++index) {
    std::array<unsigned char, 112> raw{};
    f.read(reinterpret_cast<char *>(raw.data()), raw.size());
    if (!f)
      return 4;
    std::array<std::uint32_t, 28> v{};
    for (unsigned i = 0; i < v.size(); ++i)
      v[i] = word(raw.data() + 4 * i);
    unsigned op = v[0], arg = v[1];
    if (op > 3 || arg > 1 || v[2] > 255)
      return 5;
    Context c;
    c.handlerResult = v[5];
    c.sendResult = arg;
    c.payload = {v[9], v[10]};
    presonus::uc::ConnectionState common;
    common.context = &c;
    common.queryPayload = [](void *p, const Event &) {
      return static_cast<Context *>(p)->payload;
    };
    common.sendReply = [](void *p, const presonus::uc::ConnectionReplyView &r) {
      auto &c = *static_cast<Context *>(p);
      ++c.sendCalls;
      c.reply = {r.header.type,   r.header.reserved04, r.header.routeA,
                 r.header.routeB, r.payloadWords[0],   r.payloadWords[1]};
      return bool(c.sendResult);
    };
    presonus::uc::ExternalConnectionState state;
    state.routeBits = v[3];
    state.orientation = static_cast<unsigned char>(v[2]);
    state.handlerContext = &c;
    if (v[4])
      state.handle = [](void *p, void *origin, const Event &event) {
        auto &c = *static_cast<Context *>(p);
        ++c.handlerCalls;
        c.invalidOrigin = origin != nullptr;
        c.snapshot = event;
        return signedBits(c.handlerResult);
      };
    hierarchy_test::LiveBasicState basic;
    hierarchy_test::ConcreteExternalConnection connection(state, common,
                                                          basic.basic);
    Event event{v[6], 0x12345678u, v[7], v[8]};
    const Event before = event;
    unsigned result = 0, addressOK = 0;
    unsigned short port = 0xa5a5;
    const char *address = "initial";
    switch (op) {
    case 0:
      connection.adjustRouting(event, arg);
      break;
    case 1:
      result = connection.handleInternal(event);
      break;
    case 2:
      result = connection.getType();
      break;
    case 3:
      connection.getAddress(address, port);
      addressOK = address && std::strcmp(address, "(External)") == 0;
      break;
    }
    std::array<std::uint32_t, 17> actual = {
        result,     c.handlerCalls,   c.sendCalls,  addressOK,    port,
        event.type, event.reserved04, event.routeA, event.routeB, v[9],
        v[10],      c.reply[0],       c.reply[1],   c.reply[2],   c.reply[3],
        c.reply[4], c.reply[5]};
    for (unsigned i = 0; i < actual.size(); ++i)
      if (actual[i] != v[11 + i]) {
        std::fprintf(stderr, "fixture%u op%u word%u got%08x want%08x\n", index,
                     op, i, actual[i], v[11 + i]);
        return 6;
      }
    if (c.invalidOrigin || state.routeBits != v[3] || state.orientation != v[2])
      return 7;
    if (op != 0 && std::memcmp(&before, &event, sizeof(event)))
      return 8;
    if (c.handlerCalls && std::memcmp(&c.snapshot, &before, sizeof(before)))
      return 9;
  }
  if (f.peek() != std::char_traits<char>::eof())
    return 10;
  std::printf("%u original ARM ExternalConnection fixtures passed\n", records);
}
