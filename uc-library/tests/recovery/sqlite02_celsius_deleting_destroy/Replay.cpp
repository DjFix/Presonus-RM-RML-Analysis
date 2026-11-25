#include "presonus/uc/Celsius.hpp"
#include <array>
#include <cstring>
#include <iostream>

namespace {
const void *tracked;
int releases;

[[gnu::noinline]] void destroy(Core::Formatter *formatter) { delete formatter; }

bool sameProvider(const Core::Formatter &value,
                  const Core::IntFormatter &base) {
  std::array<char, 64> got{}, expected{};
  Core::Formatter::Data candidate{nullptr, got.data(), 64, -21.f, nullptr};
  Core::Formatter::Data reference{nullptr, expected.data(), 64, -21.f, nullptr};
  value.print(candidate);
  base.print(reference);
  if (got != expected || std::strcmp(value.getName(), base.getName()) != 0)
    return false;
  std::strcpy(got.data(), "37");
  std::strcpy(expected.data(), "37");
  return value.scan(candidate) && base.scan(reference) &&
         candidate.value == reference.value;
}
} // namespace

extern "C" {
void __real__ZdlPv(void *);
void __real__ZdlPvm(void *, std::size_t);
void __wrap__ZdlPv(void *pointer) {
  const bool match = pointer == tracked;
  __real__ZdlPv(pointer);
  if (match)
    ++releases;
}
void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  const bool match = pointer == tracked;
  __real__ZdlPvm(pointer, size);
  if (match)
    ++releases;
}
}

int main(int argc, char **argv) {
  if (argc != 2 && argc != 3)
    return 1;
  std::array<char, 32> observed{};
  const char *label = nullptr;
  if (argc == 3) {
    if (std::strlen(argv[2]) >= observed.size())
      return 2;
    std::strcpy(observed.data(), argv[2]);
    label = observed.data();
  }
  const auto before = observed;
  Core::IntFormatter base("temperature", label);
  using Presonus::UC::Format::Celsius;
  if (std::strcmp(argv[1], "deleting_destroy") == 0) {
    auto *object = new Celsius("temperature", label);
    if (!sameProvider(*object, base)) {
      delete object;
      return 3;
    }
    tracked = object;
    destroy(object);
  } else {
    Celsius object("temperature", label);
    tracked = &object;
    if (!sameProvider(object, base))
      return 4;
  }
  std::cout << releases << ' ' << (observed == before) << '\n';
}
