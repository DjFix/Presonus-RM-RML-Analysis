#include "presonus/panel/simulate_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <new>
#include <vector>
using Presonus::Panel::SimulateComm;
using Access = presonus::panel::SimulateCommAccess;
extern "C" void simulate_c1(SimulateComm *,
                            bool) asm("_ZN8Presonus5Panel12SimulateCommC1Eb");
extern "C" void simulate_c2(SimulateComm *,
                            bool) asm("_ZN8Presonus5Panel12SimulateCommC2Eb");
extern "C" void
simulate_d2(SimulateComm *) asm("_ZN8Presonus5Panel12SimulateCommD2Ev");
extern "C" void
simulate_d1(SimulateComm *) asm("_ZN8Presonus5Panel12SimulateCommD1Ev");
extern "C" void
simulate_d0(SimulateComm *) asm("_ZN8Presonus5Panel12SimulateCommD0Ev");
extern "C" void simulate_virtual_delete(Presonus::Panel::ProtocolComm *);
extern "C" void simulate_virtual_destroy(Presonus::Panel::ProtocolComm *);
struct Context {
  bool enabled = false, freedFirst = false, freedSecond = false;
  void *object = nullptr, *platform = nullptr;
  char *first = nullptr, *second = nullptr;
  unsigned depth = 0, allocations = 0;
  std::array<unsigned char, 128> firstImage{}, secondImage{};
  std::vector<unsigned> events;
};
static Context *context;
extern "C" void __real__ZN4Core8Platform9PosixLockC1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockC1Ev(void *p) {
  if (context) {
    context->platform = p;
    if (context->enabled)
      context->events.push_back(1);
  }
  __real__ZN4Core8Platform9PosixLockC1Ev(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  if (context && context->enabled) {
    if (p != context->platform)
      std::abort();
    context->events.push_back(2);
    ++context->depth;
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (context && context->enabled) {
    if (p != context->platform || !context->depth)
      std::abort();
    context->events.push_back(3);
    --context->depth;
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLockD1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockD1Ev(void *p) {
  if (context && context->enabled) {
    if (p != context->platform || context->depth)
      std::abort();
    context->events.push_back(4);
  }
  __real__ZN4Core8Platform9PosixLockD1Ev(p);
}
void *operator new[](std::size_t size) {
  void *p = std::malloc(size);
  if (!p)
    throw std::bad_alloc();
  if (context && context->enabled) {
    if (size != 0x19000 || context->allocations >= 2)
      std::abort();
    auto index = context->allocations++;
    context->events.push_back(5 + index);
    std::memcpy(
        p, index ? context->secondImage.data() : context->firstImage.data(),
        128);
    if (index)
      context->second = static_cast<char *>(p);
    else
      context->first = static_cast<char *>(p);
  }
  return p;
}
void operator delete[](void *p) noexcept {
  if (context) {
    if (p == context->first) {
      if (context->freedFirst)
        std::abort();
      context->freedFirst = true;
      if (context->enabled)
        context->events.push_back(7);
    }
    if (p == context->second) {
      if (context->freedSecond)
        std::abort();
      context->freedSecond = true;
      if (context->enabled)
        context->events.push_back(8);
    }
  }
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
void operator delete(void *p) noexcept {
  if (context && context->enabled && p == context->object)
    context->events.push_back(9);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static int integer(unsigned n) {
  int result;
  std::memcpy(&result, &n, 4);
  return result;
}
static void append(std::vector<unsigned char> &v, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    v.push_back(static_cast<unsigned char>(n >> (i * 8)));
}
static unsigned identity(const Context &c, const char *p) {
  if (!p)
    return 0;
  if (p == c.first)
    return 1;
  if (p == c.second)
    return 2;
  std::abort();
}
static std::vector<unsigned char>
run(const std::array<unsigned char, 400> &input) {
  const auto op = word(input.data()), flags = word(input.data() + 4),
             count = word(input.data() + 8),
             instances = word(input.data() + 12);
  Context c;
  c.events.reserve(16);
  std::memcpy(c.firstImage.data(), input.data() + 16, 128);
  std::memcpy(c.secondImage.data(), input.data() + 144, 128);
  char *originalFirst = static_cast<char *>(std::malloc(0x19000)),
       *originalSecond = static_cast<char *>(std::malloc(0x19000));
  if (!originalFirst || !originalSecond)
    std::abort();
  c.first = originalFirst;
  c.second = originalSecond;
  std::memcpy(c.first, c.firstImage.data(), 128);
  std::memcpy(c.second, c.secondImage.data(), 128);
  auto *a = (flags & 2) ? nullptr : c.first;
  auto *b = (flags & 4) ? nullptr : c.second;
  auto *object =
      static_cast<SimulateComm *>(::operator new(sizeof(SimulateComm)));
  c.object = object;
  context = &c;
  Access::shared(a, b, (op == 5 || op == 6) ? instances : 1);
  if (op == 5 || op == 6) {
    c.enabled = true;
    if (op == 5)
      simulate_c1(object, flags & 1);
    else
      simulate_c2(object, flags & 1);
  } else {
    simulate_c1(object, flags & 1);
    Access::shared(a, b, instances);
    c.enabled = true;
  }
  unsigned readId = identity(c, Access::input(*object)),
           writeId = identity(c, Access::output(*object));
  std::array<unsigned char, 128> output;
  output.fill(0xcc);
  std::array<unsigned char, 256> arrays;
  std::memcpy(arrays.data(), c.first, 128);
  std::memcpy(arrays.data() + 128, c.second, 128);
  unsigned result = 0;
  if (op == 0)
    result =
        object->read(reinterpret_cast<char *>(output.data()), integer(count));
  else if (op == 1)
    result = object->write(reinterpret_cast<const char *>(input.data() + 272),
                           integer(count));
  else if (op == 2)
    result = object->open(reinterpret_cast<const char *>(input.data() + 272));
  else if (op == 3)
    object->close();
  else if (op == 4)
    result = object->enableHISpeed(flags & 1);
  else if (op == 7)
    simulate_virtual_destroy(object);
  else if (op == 8)
    simulate_d2(object);
  else if (op == 9)
    simulate_virtual_delete(object);
  else if (op != 5 && op != 6)
    std::abort();
  if (op < 7) {
    std::memcpy(arrays.data(), c.first, 128);
    std::memcpy(arrays.data() + 128, c.second, 128);
  }
  if (c.depth || c.events.size() > 16)
    std::abort();
  std::vector<unsigned char> actual;
  for (unsigned n : {result, Access::instances(), readId, writeId,
                     static_cast<unsigned>(c.events.size())})
    append(actual, n);
  for (unsigned event : c.events)
    append(actual, event);
  for (unsigned i = c.events.size(); i < 16; ++i)
    append(actual, 0);
  actual.insert(actual.end(), arrays.begin(), arrays.end());
  actual.insert(actual.end(), output.begin(), output.end());
  c.enabled = false;
  if (op < 7) {
    Access::shared(c.first, c.second, 1);
    simulate_virtual_destroy(object);
  }
  if (!c.freedFirst)
    ::operator delete[](c.first);
  if (!c.freedSecond)
    ::operator delete[](c.second);
  if (c.first != originalFirst)
    std::free(originalFirst);
  if (c.second != originalSecond)
    std::free(originalSecond);
  if (op != 9)
    ::operator delete(object);
  Access::shared(nullptr, nullptr, 0);
  context = nullptr;
  return actual;
}
static void composition() {
  Access::shared(nullptr, nullptr, 0);
  {
    SimulateComm left(false), right(true);
    if (Access::instances() != 2)
      std::abort();
    void **slots = nullptr;
    std::memcpy(&slots, &left, sizeof(slots));
    if (slots[6] != reinterpret_cast<void *>(simulate_d1) ||
        slots[7] != reinterpret_cast<void *>(simulate_d0))
      std::abort();
    if (left.open("ignored") != 1)
      std::abort();
    if (left.write("ABC", 3) != 3)
      std::abort();
    char out[8];
    std::memset(out, 0xcc, 8);
    if (right.read(out, 4) != 0 || out[0] != 0)
      std::abort();
    if (right.read(out, 3) != 3 || std::memcmp(out, "ABC", 3) ||
        static_cast<unsigned char>(out[3]) != 0xcc)
      std::abort();
    if (right.write("XY\0tail", 7) != 7 || left.read(out, 2) != 2 ||
        std::memcmp(out, "XY", 2))
      std::abort();
    Uart_Msg_Type send{{'G', 3, 0x23, 1}}, receive{{0, 0, 0, 0}};
    if (left.writeMsg(send) != 1 || right.readMsg(receive) != 1 ||
        receive.bytes != send.bytes)
      std::abort();
    if (right.open("reset both") != 1 || left.read(out, 1) != 0)
      std::abort();
  }
  if (Access::instances() != 0)
    std::abort();
  Access::shared(nullptr, nullptr, 0);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), 12);
  if (!f || std::memcmp(header.data(), "SIMCv001", 8))
    return 3;
  const auto count = word(header.data() + 8);
  for (unsigned index = 0; index < count; ++index) {
    std::array<unsigned char, 400> input;
    std::array<unsigned char, 468> expected;
    f.read(reinterpret_cast<char *>(input.data()), input.size());
    f.read(reinterpret_cast<char *>(expected.data()), expected.size());
    if (!f)
      return 4;
    auto actual = run(input);
    if (actual.size() != expected.size())
      return 5;
    for (unsigned i = 0; i < expected.size(); ++i)
      if (actual[i] != expected[i]) {
        std::fprintf(
            stderr,
            "Mismatch case%u op%u flags%u offset%u expected%u actual%u\n",
            index, word(input.data()), word(input.data() + 4), i, expected[i],
            actual[i]);
        return 6;
      }
  }
  composition();
  std::printf("PASS %u original SimulateComm fixtures plus duplex/framing "
              "composition\n",
              count);
}
