#include "presonus/DefaultMeterInterpolator.hpp"

#include <cstdlib>
#include <iostream>
#include <new>

namespace {
const void *tracked = nullptr;
unsigned deallocations = 0;

[[gnu::noipa]] void destroy(Core::Interpolator *interpolator) {
  delete interpolator;
}
} // namespace

void *operator new(std::size_t size) {
  if (auto *pointer = std::malloc(size == 0 ? 1 : size))
    return pointer;
  throw std::bad_alloc();
}
void operator delete(void *pointer) noexcept {
  if (pointer == tracked)
    ++deallocations;
  std::free(pointer);
}
void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

int main() {
  const Core::SegmentInterpolator::BreakPoint points[] = {{0.f, -60.f},
                                                          {1.f, 0.f}};
  auto *interpolator = new DefaultMeterInterpolator(2, points);
  tracked = interpolator;
  destroy(interpolator);
  tracked = nullptr;
  std::cout << deallocations << '\n';
}
