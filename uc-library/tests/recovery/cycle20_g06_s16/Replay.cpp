#include "presonus/panel/Element.hpp"
#include "presonus/panel/OffscreenElement.hpp"

#include <cerrno>
#include <cstddef>
#include <iostream>
#include <new>
#include <string_view>
#include <sys/mman.h>

using Presonus::Panel::Element;
using Presonus::Panel::OffscreenElement;

namespace {
void *mappedReceiver = nullptr;
int disposalResult = -1;
bool mapNextAllocation = false;
} // namespace

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  if (!mapNextAllocation)
    return __real__Znwm(size);

  mapNextAllocation = false;
  mappedReceiver = mmap(nullptr, 4096, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (mappedReceiver == MAP_FAILED)
    throw std::bad_alloc{};
  return mappedReceiver;
}

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *receiver) {
  if (mappedReceiver && receiver == mappedReceiver) {
    disposalResult = munmap(receiver, 4096);
    return;
  }
  __real__ZdlPv(receiver);
}

[[gnu::noinline]] void destroy(Element *receiver) { delete receiver; }

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string_view mode(argv[1]);
  if (mode == "element-constructor" || mode == "offscreen-constructor") {
    int x, y;
    while (std::cin >> x >> y) {
      if (mode == "element-constructor") {
        Element element(x, y);
        const auto &state = element.elementState();
        std::cout << state.x << ' ' << state.y << ' ' << state.dirty << ' '
                  << state.activation << '\n';
      } else {
        OffscreenElement element(x, y);
        const auto &state = element.elementState();
        std::cout << state.x << ' ' << state.y << ' ' << state.dirty << ' '
                  << state.activation << '\n';
      }
    }
  } else if (mode == "activation") {
    int prior, next;
    unsigned int dirty;
    while (std::cin >> prior >> next >> dirty) {
      Element element;
      element.activate(prior);
      element.setDirty(dirty);
      element.activate(next);
      const auto &state = element.elementState();
      std::cout << state.dirty << ' ' << state.activation << '\n';
    }
  } else {
    char variant;
    while (std::cin >> variant) {
      disposalResult = -1;
      if (variant == '0') {
        mapNextAllocation = true;
        destroy(new OffscreenElement(0, 0));
      } else {
        mappedReceiver = mmap(nullptr, 4096, PROT_READ | PROT_WRITE,
                              MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (mappedReceiver == MAP_FAILED)
          return 3;
        auto *element = ::new (mappedReceiver) OffscreenElement(0, 0);
        element->~OffscreenElement();
      }

      unsigned char residence;
      errno = 0;
      const int result = mincore(mappedReceiver, 4096, &residence);
      if (variant == '0') {
        if (disposalResult != 0 || result != -1 || errno != ENOMEM)
          return 4;
        std::cout << "freed\n";
      } else {
        if (disposalResult != -1 || result != 0 ||
            munmap(mappedReceiver, 4096) != 0)
          return 5;
        std::cout << "retained\n";
      }
      mappedReceiver = nullptr;
    }
  }
}
