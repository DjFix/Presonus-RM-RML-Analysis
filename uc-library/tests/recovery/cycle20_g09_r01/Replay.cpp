#include "presonus/mixer/EarlyRefFormatterT3.hpp"
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <sys/mman.h>
#include <unistd.h>

namespace {
using Tagged = Presonus::Mixer::EarlyRefFormatterT3;
using Parent = Presonus::Mixer::EarlyRefFormatter;
void *watched;
std::size_t pageSize;
unsigned deletes;
bool allocateMapped;

void destroy(Core::Formatter *object) { delete object; }

void require(bool success) {
  if (!success)
    throw std::runtime_error("formatter lifecycle observation differed");
}

bool mapped(void *memory) {
  unsigned char residency = 0;
  if (mincore(memory, pageSize, &residency) == 0)
    return true;
  require(errno == ENOMEM);
  return false;
}

std::array<char, 32> print(const Core::Formatter &object, float value) {
  std::array<char, 32> output;
  output.fill('x');
  Core::Formatter::Data data{nullptr, output.data(), int(output.size()), value,
                             nullptr};
  object.print(data);
  require(data.value == value && !object.scan(data) && data.value == value);
  return output;
}
} // namespace

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  if (!allocateMapped)
    return __real__Znwm(size);
  allocateMapped = false;
  if (size != sizeof(Tagged))
    throw std::bad_alloc{};
  void *storage = mmap(nullptr, pageSize, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (storage == MAP_FAILED)
    throw std::bad_alloc{};
  watched = storage;
  return storage;
}

extern "C" void __real__ZdlPv(void *address) noexcept;
extern "C" void __wrap__ZdlPv(void *address) noexcept {
  if (address != watched || !watched) {
    __real__ZdlPv(address);
    return;
  }
  if (++deletes != 1 || munmap(address, pageSize) != 0)
    std::terminate();
}

int main() {
  const long systemPageSize = sysconf(_SC_PAGESIZE);
  require(systemPageSize > 0);
  pageSize = static_cast<std::size_t>(systemPageSize);
  std::string expectedName;
  unsigned seed;
  while (std::cin >> expectedName >> seed) {
    presonus::mixer::registerEarlyRefFormatterT3();
    auto *registered = Core::FormatterRegistry::find(expectedName.c_str());
    require(registered && expectedName == registered->getName());
    presonus::mixer::registerEarlyRefFormatterT3();
    require(Core::FormatterRegistry::find(expectedName.c_str()) == registered);
    const Parent parent;
    const float value = seed * 0.125f;
    const auto expected = print(parent, value);
    require(print(*registered, value) == expected);
    allocateMapped = true;
    auto *object = new Tagged;
    require(watched == object && !allocateMapped);
    require(expectedName == object->getName() &&
            print(*object, value) == expected);
    deletes = 0;
    object->~Tagged();
    require(deletes == 0 && mapped(watched));
    require(munmap(watched, pageSize) == 0);
    watched = nullptr;
    allocateMapped = true;
    object = new Tagged;
    require(watched == object && !allocateMapped);
    destroy(object);
    require(deletes == 1 && !mapped(watched));
    watched = nullptr;
    std::cout << expectedName << ' ' << seed << " 1 0\n";
  }
  return std::cin.eof() ? 0 : 2;
}
