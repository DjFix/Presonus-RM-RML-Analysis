#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>
using Presonus::Panel::ProtocolComm;
using Access = presonus::panel::ProtocolCommAccess;
extern "C" void
protocol_d1(ProtocolComm *) asm("_ZN8Presonus5Panel12ProtocolCommD1Ev");
extern "C" void
protocol_d2(ProtocolComm *) asm("_ZN8Presonus5Panel12ProtocolCommD2Ev");
extern "C" void
protocol_d0(ProtocolComm *) asm("_ZN8Presonus5Panel12ProtocolCommD0Ev");
extern "C" void protocol_delete_concrete(ProtocolComm *);
struct Context {
  bool enabled = false;
  void *object = nullptr, *platform = nullptr;
  unsigned constructors = 0, depth = 0, deletes = 0, cursor = 0, reads = 0,
           writes = 0, writeCount = 0;
  unsigned length = 0, end = 0, reply = 0;
  std::array<char, 96> stream{};
  std::array<unsigned char, 16> written{};
  std::vector<unsigned> events;
};
static Context *context;
extern "C" void __real__ZN4Core8Platform9PosixLockC1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockC1Ev(void *p) {
  if (context) {
    ++context->constructors;
    context->platform = p;
  }
  __real__ZN4Core8Platform9PosixLockC1Ev(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  if (context && context->enabled) {
    if (p != context->platform)
      std::abort();
    context->events.push_back(1);
    ++context->depth;
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (context && context->enabled) {
    if (p != context->platform || !context->depth)
      std::abort();
    context->events.push_back(2);
    --context->depth;
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLockD1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockD1Ev(void *p) {
  if (context && context->enabled) {
    if (p != context->platform || context->depth)
      std::abort();
    context->events.push_back(5);
  }
  __real__ZN4Core8Platform9PosixLockD1Ev(p);
}
void operator delete(void *p) noexcept {
  if (context && context->enabled && p == context->object) {
    context->events.push_back(6);
    ++context->deletes;
  }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
static int integer(unsigned n) {
  int v;
  std::memcpy(&v, &n, 4);
  return v;
}
// Independent test transport: real production base/framing; only raw I/O is an
// explicit external transcript. Unused pure interface methods abort, never fake
// successful base behavior.
class Transcript final : public ProtocolComm {
public:
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
  int read(char *out, int count) override {
    auto &c = *context;
    if (this != c.object || count != 1)
      std::abort();
    c.events.push_back(3);
    ++c.reads;
    if (c.cursor < c.length) {
      *out = c.stream[c.cursor++];
      return 1;
    }
    return integer(c.end);
  }
  int write(const char *text, int count) override {
    auto &c = *context;
    if (this != c.object || count <= 0 || count > 16)
      std::abort();
    c.events.push_back(4);
    ++c.writes;
    c.writeCount = count;
    std::memcpy(c.written.data(), text, count);
    return integer(c.reply);
  }
};
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static void append(std::vector<unsigned char> &out, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    out.push_back(static_cast<unsigned char>(n >> (8 * i)));
}
static std::vector<unsigned char>
run(const std::array<unsigned char, 160> &input) {
  unsigned op = word(input.data());
  Context c;
  c.events.reserve(128);
  c.length = word(input.data() + 4);
  c.end = word(input.data() + 8);
  c.reply = word(input.data() + 12);
  c.written.fill(0xcc);
  if (c.length > 96)
    std::abort();
  std::memcpy(c.stream.data(), input.data() + 60, 96);
  context = &c;
  auto *object = new Transcript;
  c.object = object;
  if (c.constructors != 1 || !c.platform)
    std::abort();
  Uart_Msg_Type message;
  std::memcpy(message.bytes.data(), input.data() + 24, 4);
  std::memcpy(Access::receive(*object), input.data() + 28, 32);
  Access::prefix(*object, static_cast<char>(input[156]),
                 static_cast<char>(input[157]));
  std::array<unsigned char, 32> receive;
  std::memcpy(receive.data(), Access::receive(*object), 32);
  c.enabled = true;
  unsigned result = 0;
  if (op == 0)
    result = object->readMsg(message);
  else if (op == 1)
    result = object->writeMsg(message);
  else if (op == 2)
    result = object->broadcast(reinterpret_cast<Presonus::Panel::Control *>(
        static_cast<std::uintptr_t>(word(input.data() + 16))));
  else if (op == 3)
    protocol_d1(object);
  else if (op == 4)
    protocol_d2(object);
  else if (op == 5)
    protocol_d0(object);
  else
    std::abort();
  // No post-lifetime reads: receive state for destructor rows is a pre-teardown
  // diagnostic, not a claim about destroyed native object bytes/vptrs.
  if (op < 3)
    std::memcpy(receive.data(), Access::receive(*object), 32);
  if (c.depth || c.events.size() > 128)
    std::abort();
  std::vector<unsigned char> output;
  for (unsigned n :
       {result, c.reads, c.cursor, c.writes, c.writeCount,
        static_cast<unsigned>(c.events.size()), c.deletes, c.depth})
    append(output, n);
  output.insert(output.end(), message.bytes.begin(), message.bytes.end());
  output.insert(output.end(), receive.begin(), receive.end());
  output.insert(output.end(), c.written.begin(), c.written.end());
  for (unsigned event : c.events)
    append(output, event);
  for (unsigned i = c.events.size(); i < 128; ++i)
    append(output, 0);
  c.enabled = false;
  if (op < 3)
    delete object;
  else if (op != 5)
    ::operator delete(object);
  context = nullptr;
  return output;
}
static void virtualLifetime() {
  Context c;
  c.events.reserve(128);
  context = &c;
  auto *object = new Transcript;
  c.object = object;
  c.enabled = true;
  protocol_delete_concrete(object);
  if (c.events != std::vector<unsigned>{5, 6} || c.deletes != 1 ||
      c.constructors != 1)
    std::abort();
  c.enabled = false;
  context = nullptr;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "UPCMv001", 8))
    return 3;
  unsigned count = word(header.data() + 8);
  for (unsigned index = 0; index < count; ++index) {
    std::array<unsigned char, 160> input{};
    std::array<unsigned char, 596> expected{};
    f.read(reinterpret_cast<char *>(input.data()), input.size());
    f.read(reinterpret_cast<char *>(expected.data()), expected.size());
    if (!f)
      return 4;
    auto actual = run(input);
    if (actual.size() != expected.size() ||
        std::memcmp(actual.data(), expected.data(), expected.size())) {
      unsigned at = 0;
      while (at < expected.size() && actual[at] == expected[at])
        ++at;
      std::fprintf(
          stderr,
          "protocol fixture%u op%u n%u end%u reply%u byte%u got%u want%u\n",
          index, word(input.data()), word(input.data() + 4),
          word(input.data() + 8), word(input.data() + 12), at, actual[at],
          expected[at]);
      return 5;
    }
  }
  virtualLifetime();
  std::printf("%u original ARM ProtocolComm state/lifecycle fixtures passed; "
              "real CCL ctor/lock/unlock/dtor and genuine delete observed; "
              "concrete virtual lifetime passed\n",
              count);
}
