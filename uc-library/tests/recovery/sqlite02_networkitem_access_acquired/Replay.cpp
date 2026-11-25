#include "presonus/uc/NetworkItem.hpp"
#include <cstdint>
#include <iostream>

int main() {
  int borrowedComponent = 42;
  Presonus::UC::NetworkItem first(&borrowedComponent);
  Presonus::UC::NetworkItem second(nullptr);
  std::cout << first.isAccessAcquired() << ' ' << second.isAccessAcquired()
            << '\n';
  for (std::uint32_t observation : {1U, 0x80000000U, 0xffffffffU, 0U}) {
    first.setPortableAccessObservation(observation);
    std::cout << first.isAccessAcquired() << ' ' << second.isAccessAcquired()
              << '\n';
  }
  return first.getComponent() == &borrowedComponent &&
                 second.getComponent() == nullptr
             ? 0
             : 1;
}
