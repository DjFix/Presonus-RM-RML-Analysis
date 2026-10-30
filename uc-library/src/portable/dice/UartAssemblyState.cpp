#include "presonus/dice/uart_assembly.hpp"
#include <cstring>
#include <new>
#include <stdexcept>

namespace presonus::dice {
UartAssemblyState::UartAssemblyState(const std::array<unsigned char, 67> &seed,
                                     unsigned char countSeed,
                                     int receiverCapacity)
    : count(countSeed), receivers(receiverCapacity),
      storage_(Core::uint32(seed.size())) {
  if (receiverCapacity < 0)
    throw std::invalid_argument("nonnegative independent receiver capacity");
  if (!storage_.getAddress())
    throw std::bad_alloc();
  std::memcpy(storage_.getAddress(), seed.data(), seed.size());
}
} // namespace presonus::dice
