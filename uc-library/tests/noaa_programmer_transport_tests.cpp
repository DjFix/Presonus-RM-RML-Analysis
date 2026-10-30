#include "presonus/noaa/programmer.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <new>
#include <sstream>
#include <string>
#include <typeinfo>
#include <unistd.h>
#include <vector>

using presonus::noaa::ProgrammerAccess;
using Presonus::NOAA::TCardProgrammer;

struct Capture {
  void *object = nullptr;
  const void *descriptorAddress = nullptr;
  bool expectAllocation = false, observeDelete = false, freed = false;
  unsigned allocations = 0, frees = 0;
  std::vector<std::string> events;
};
static Capture *active = nullptr;
static unsigned allocations = 0, frees = 0, actualDeletingVariants = 0,
                actualNondeletingVariants = 0;

static std::string hex(const unsigned char *data, unsigned count) {
  static const char digits[] = "0123456789abcdef";
  std::string result;
  for (unsigned i = 0; i < count; ++i) {
    result += digits[data[i] >> 4];
    result += digits[data[i] & 15];
  }
  return result.empty() ? "-" : result;
}
static std::uint32_t descriptorWord() {
  std::uint32_t result;
  assert(active && active->descriptorAddress && !active->freed);
  std::memcpy(&result, active->descriptorAddress, sizeof result);
  return result;
}

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  void *p = __real__Znwm(n);
  if (active && active->expectAllocation) {
    assert(n == sizeof(TCardProgrammer));
    active->object = p;
    active->expectAllocation = false;
    ++active->allocations;
    ++allocations;
  }
  return p;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static bool beforeDelete(void *p) {
  const bool matches = active && p == active->object;
  if (matches) {
    assert(!active->freed);
    if (active->observeDelete)
      assert(descriptorWord() == 0xffffffffu);
  }
  return matches;
}
static void afterDelete(bool matches) {
  if (matches) {
    active->freed = true;
    ++active->frees;
    ++frees;
    if (active->observeDelete)
      active->events.emplace_back("D"); // Only after the actual deallocator.
  }
}
extern "C" void __wrap__ZdlPv(void *p) {
  const auto matches = beforeDelete(p);
  __real__ZdlPv(p);
  afterDelete(matches);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  const auto matches = beforeDelete(p);
  __real__ZdlPvm(p, n);
  afterDelete(matches);
}

struct Script final : presonus::noaa::ProgrammerTransport {
  std::vector<std::int32_t> returns;
  unsigned index = 0;
  std::int32_t write(std::int32_t fd, const unsigned char *data,
                     std::uint32_t count) override {
    assert(active && !returns.empty());
    active->events.push_back(
        "W:" + std::to_string(static_cast<std::uint32_t>(fd)) + ":" +
        std::to_string(count) + ":" +
        (count > 512 ? "OPAQUE" : hex(data, count)));
    return returns[index++ % returns.size()];
  }
  std::int32_t close(std::int32_t fd) override {
    assert(active && !returns.empty());
    active->events.push_back("C:" +
                             std::to_string(static_cast<std::uint32_t>(fd)));
    return returns[0];
  }
};

extern "C" void
ctorC1(TCardProgrammer *, Presonus::UC::IFirmwareUpdateListener *,
       const unsigned char *,
       unsigned int) asm("_ZN8Presonus4NOAA15TCardProgrammerC1EPNS_"
                         "2UC23IFirmwareUpdateListenerEPKhj");
extern "C" void
ctorC2(TCardProgrammer *, Presonus::UC::IFirmwareUpdateListener *,
       const unsigned char *,
       unsigned int) asm("_ZN8Presonus4NOAA15TCardProgrammerC2EPNS_"
                         "2UC23IFirmwareUpdateListenerEPKhj");
extern "C" void
dtorD1(TCardProgrammer *) asm("_ZN8Presonus4NOAA15TCardProgrammerD1Ev");
extern "C" void
dtorD2(TCardProgrammer *) asm("_ZN8Presonus4NOAA15TCardProgrammerD2Ev");
extern "C" void
dtorD0(TCardProgrammer *) asm("_ZN8Presonus4NOAA15TCardProgrammerD0Ev");

int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  std::string line;
  unsigned cases = 0, constructors = 0;
  while (std::getline(input, line)) {
    std::istringstream in(line);
    std::string method;
    std::int32_t fd;
    long long length;
    unsigned seed, image, count;
    std::uint32_t argument, listener;
    in >> method >> fd >> length >> seed >> argument >> listener >> image >>
        count;
    Script io;
    io.returns.resize(count);
    for (auto &value : io.returns)
      in >> value;
    in >> count;
    std::vector<std::string> expected(count);
    for (auto &event : expected)
      in >> event;
    std::uint32_t expectedDescriptor, expectedResult;
    in >> expectedDescriptor >> expectedResult;
    assert(in && seed <= 255 && image <= 1);
    std::array<unsigned char, 512> data;
    for (unsigned i = 0; i < data.size(); ++i)
      data[i] = static_cast<unsigned char>(seed + i * 29);
    Capture capture;
    active = &capture;
    capture.expectAllocation = true;
    void *storage = ::operator new(sizeof(TCardProgrammer));
    std::memset(storage, seed, sizeof(TCardProgrammer));
    auto *object = static_cast<TCardProgrammer *>(storage);
    const bool ctor = method == "C1" || method == "C2";
    auto *listenerValue =
        reinterpret_cast<Presonus::UC::IFirmwareUpdateListener *>(
            std::uintptr_t(listener));
    if (method == "C2")
      ctorC2(object, listenerValue, image ? data.data() : nullptr,
             static_cast<unsigned int>(length));
    else
      ctorC1(object, ctor ? listenerValue : nullptr,
             ctor ? (image ? data.data() : nullptr) : data.data(),
             ctor ? static_cast<unsigned int>(length) : 512);
    assert(typeid(*object) == typeid(TCardProgrammer));
    assert(std::strcmp(typeid(*object).name(),
                       "N8Presonus4NOAA15TCardProgrammerE") == 0);
    const auto &state = ProgrammerAccess::state(*object);
    capture.descriptorAddress = &state.descriptor;
    assert(state.descriptor == -1 && state.word16 == 115200 &&
           state.byte24 == 0);
    for (auto word : state.words28to40)
      assert(word == 0);
    if (ctor) {
      assert(state.image == (image ? data.data() : nullptr) &&
             state.listener == listenerValue &&
             state.length == static_cast<unsigned int>(length));
      ++constructors;
    }
    ProgrammerAccess::bind(*object, io, ctor ? -1 : fd);
    std::uint32_t result = 0;
    if (method == "calcCRC")
      result = object->calcCRC(data.data(), static_cast<int>(length));
    else if (method == "write")
      result = object->write(data.data(), static_cast<int>(length));
    else if (method == "writeChar")
      result = object->writeChar(static_cast<unsigned char>(argument));
    else if (method == "sendPacket")
      result = object->sendPacket(data.data(), static_cast<int>(length));
    else if (method == "sendAddress")
      result = object->sendAddress(argument);
    else if (method == "close")
      result = object->close();
    else if (method == "D1") {
      dtorD1(object);
      ++actualNondeletingVariants;
    } else if (method == "D2") {
      dtorD2(object);
      ++actualNondeletingVariants;
    } else if (method == "D0") {
      capture.observeDelete = true;
      dtorD0(object);
      ++actualDeletingVariants;
    } else
      assert(ctor);
    assert(capture.events == expected);
    if (method != "D0") {
      if (capture.freed || descriptorWord() != expectedDescriptor)
        std::fprintf(
            stderr,
            "case %u method %s fd %d expected %08x actual %08x freed %d\n",
            cases, method.c_str(), fd, expectedDescriptor,
            capture.freed ? 0 : descriptorWord(), capture.freed);
      assert(!capture.freed && descriptorWord() == expectedDescriptor);
      if (method != "D1" && method != "D2" && !ctor)
        assert(result == expectedResult);
      if (method != "D1" && method != "D2") {
        // Resource setup is independently controlled; lifecycle comparison is
        // performed by the dedicated original D1/D2/D0 cases above.
        ProgrammerAccess::bind(*object, io, -1);
        dtorD1(object);
      }
      assert(!capture.freed);
      ::operator delete(storage);
    }
    assert(capture.allocations == 1 && capture.frees == 1);
    active = nullptr;
    ++cases;
  }
  assert(cases == 22650 && constructors == 144 &&
         actualDeletingVariants == 126 && actualNondeletingVariants == 252);
  // Actual POSIX backend, real kernel pipe, no device path or firmware action.
  int descriptors[2];
  assert(::pipe(descriptors) == 0);
  {
    TCardProgrammer object(nullptr, nullptr, 0);
    ProgrammerAccess::bind(object, presonus::noaa::posixProgrammerTransport(),
                           descriptors[1]);
    assert(object.sendAddress(0x12345678u) == 1);
    assert(object.close() == 0);
    assert(object.close() == -1);
  }
  unsigned char received[5];
  assert(::read(descriptors[0], received, sizeof received) == 5);
  const unsigned char wanted[]{0x12, 0x34, 0x56, 0x78, 0x08};
  assert(
      std::equal(std::begin(received), std::end(received), std::begin(wanted)));
  assert(::close(descriptors[0]) == 0);
  assert(allocations == frees);
  std::printf("{\"passed\":true,\"cases\":%u,\"constructor_cases\":%u,\"actual_"
              "D0_deallocations\":%u,\"D1_D2_no_deallocation_probes\":%u,"
              "\"actual_allocations\":%u,\"actual_frees\":%u,\"actual_posix_"
              "pipe_replay\":true,\"hardware_operations\":0}\n",
              cases, constructors, actualDeletingVariants,
              actualNondeletingVariants, allocations, frees);
}
