#include "presonus/uc/server_description.hpp"

#include <array>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace {
using Subject = Presonus::UC::ServerDescription;
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
  auto *description = new (storage) Probe;
  const Core::CString64 reference(nullptr);
  require(reference.length() == 0 && reference.str()[0] == '\0');
  const std::array fields{&description->hostAddress,
                          &description->hostName,
                          &description->applicationName,
                          &description->applicationVersion,
                          &description->category,
                          &description->cid,
                          &description->pid};
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
  std::printf(
      "%d %u %u %u %u\n", description->identifier, description->contextKind,
      static_cast<unsigned>(description->port), description->flags, empty);
  description->~Probe();
}
