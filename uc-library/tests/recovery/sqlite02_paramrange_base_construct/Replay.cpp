#include "presonus/uc/param_range.hpp"

#include <array>
#include <bit>
#include <cinttypes>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace {
using Subject = Presonus::UC::ParamRange;
struct Probe final : Subject {
  Probe() : Subject() {}
};

void require(bool condition) {
  if (!condition)
    std::abort();
}
} // namespace

int main(int argc, char **argv) {
  require(argc == 2);
  alignas(Probe) std::byte storage[sizeof(Probe)];
  std::memset(storage, std::atoi(argv[1]), sizeof storage);
  auto *range = new (storage) Probe;
  const Core::CString64 reference(nullptr);
  require(reference.length() == 0 && reference.str()[0] == '\0');
  const std::array fields{&range->units, &range->curve};
  unsigned empty = 0;
  for (const auto *field : fields)
    if (field->length() == reference.length() &&
        field->str()[0] == reference.str()[0])
      ++empty;
  for (auto *field : fields) {
    *field = "set";
    require(field->length() == 3);
    for (const auto *other : fields)
      if (other != field)
        require(other->length() == 0);
    field->empty();
  }
  std::printf("%" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 " %d %u\n",
              std::bit_cast<std::uint64_t>(range->minimum),
              std::bit_cast<std::uint64_t>(range->maximum),
              std::bit_cast<std::uint64_t>(range->midpoint),
              std::bit_cast<std::uint64_t>(range->defaultValue), range->steps,
              empty);
  range->~Probe();
}
