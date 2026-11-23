#include "presonus/MeterScaleControl.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
static int failAfter = -1;
static int live = 0;
void *operator new(std::size_t n) {
  if (failAfter == 0) {
    failAfter = -1;
    throw std::bad_alloc();
  }
  if (failAfter > 0)
    --failAfter;
  if (void *p = std::malloc(n ? n : 1)) {
    ++live;
    return p;
  }
  throw std::bad_alloc();
}
void operator delete(void *p) noexcept {
  if (p) {
    --live;
    std::free(p);
  }
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
int main(int argc, char **argv) {
  using Ranges = Presonus::MeterScaleControl::Ranges;
  if (argc == 2 && std::string(argv[1]) == "failures") {
    for (int allocation : {0, 1}) {
      const int before = live;
      {
        Ranges r{Ranges::SourcePortTag{}};
        failAfter = allocation;
        bool threw = false;
        try {
          r.addRange("failure", 2, nullptr);
        } catch (const std::bad_alloc &) {
          threw = true;
        }
        failAfter = -1;
        if (!threw || r.count() != 0 || live != before)
          return 3;
        r.addRange("retry", 0, nullptr);
        if (r.count() != 1)
          return 4;
      }
      if (live != before)
        return 5;
    }
    std::cout << "2 allocation failures cleaned; retry passed\n";
    return 0;
  }
  if (argc != 4)
    return 2;
  Ranges r{Ranges::SourcePortTag{}};
  int values[] = {10, 20, 30};
  int initial = std::stoi(argv[3]);
  for (int i = 0; i < initial; ++i)
    r.addRange("duplicate", i, values);
  std::string name = argv[1];
  r.addRange(name == "@NULL" ? nullptr : name.c_str(), std::stoi(argv[2]),
             values);
  name.assign("caller name changed");
  const auto *record = r.at(initial);
  values[0] = 91;
  if (!record || record->values != values || record->values[0] != 91)
    return 6;
  if (initial && (r.getRange("duplicate") != r.at(0) || r.at(0)->count != 0))
    return 7;
  for (int i = 0; i < initial; ++i)
    if (r.at(i)->count != i)
      return 8;
  std::cout << r.count() << '\n'
            << record->name.str() << '\n'
            << record->count << '\n';
}
