#include "presonus/panel/FillElement.hpp"

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>
#include <sys/mman.h>
#include <unistd.h>

using Presonus::Panel::Element;
using Presonus::Panel::FillElement;

namespace {
void *watched;
std::size_t pageSize;
unsigned disposals;

bool isUnmapped(void *address) {
  unsigned char residency;
  errno = 0;
  return mincore(address, pageSize, &residency) == -1 && errno == ENOMEM;
}

[[gnu::noinline]] void deletingDestructor(Element *element) { delete element; }
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *receiver) {
  if (receiver == watched) {
    if (munmap(receiver, pageSize) != 0)
      std::abort();
    ++disposals;
    return;
  }
  __real__ZdlPv(receiver);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view variant(argv[1]);
  const auto requestedSeed = std::atoi(argv[2]);
  const auto size = sysconf(_SC_PAGESIZE);
  if (size <= 0)
    return 2;
  pageSize = static_cast<std::size_t>(size);
  auto *page = mmap(nullptr, pageSize, PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (page == MAP_FAILED)
    return 2;
  watched = page;
  auto *element = ::new (page) FillElement(requestedSeed, -requestedSeed);
  if (element->elementState().x != requestedSeed ||
      element->elementState().y != -requestedSeed)
    return 2;

  if (variant == "D1")
    element->FillElement::~FillElement();
  else if (variant == "D0")
    deletingDestructor(element);
  else
    return 2;
  const bool unmapped = isUnmapped(page);
  const bool consistent = variant == "D0" ? unmapped && disposals == 1
                                          : !unmapped && disposals == 0;
  if (!unmapped && munmap(page, pageSize) != 0)
    return 2;
  watched = nullptr;
  std::cout << disposals << ' ' << unmapped << '\n';
  return consistent ? 0 : 1;
}
