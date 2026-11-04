#pragma once
#include <array>
#include <cstdint>

namespace presonus::dawtime {
// Independent borrowed source-port observation state. This is not an original
// object layout or host vtable. The identity is an ELF-specific opaque token.
struct DispatchState {
  std::uint32_t identity;
  std::array<std::uint8_t, 508> unchanged;
};
} // namespace presonus::dawtime
// Partial source-port interfaces. Original full virtual interface and layout
// remain unresolved. Pointer return const qualification is provisional.
namespace Presonus {
class IDAWTimeInfo {
public:
  // State must outlive this object, so the destructor's dispatch reset remains
  // observable without reading an object after its C++ lifetime has ended.
  explicit IDAWTimeInfo(presonus::dawtime::DispatchState &state) noexcept
      : dispatchState_(state) {}
  virtual ~IDAWTimeInfo();

private:
  presonus::dawtime::DispatchState &dispatchState_;
};
} // namespace Presonus
