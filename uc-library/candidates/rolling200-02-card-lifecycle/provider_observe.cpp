#include "core/public/corestringbuffer.h"
#include <cstdint>
#include <cstdio>
#include <iostream>
int main() {
  for (unsigned serial : {0u, 0xffffffffu, 0x80000000u, 99999999u, 12345678u}) {
    Core::CStringBuffer<32> decimal(nullptr), first(nullptr), second(nullptr),
        third(nullptr), combined(nullptr);
    decimal.appendFormat("%08u", serial);
    decimal.subString(first, 0, 2);
    decimal.subString(second, 2, 2);
    decimal.subString(third, 4, 4);
    unsigned a = 0, b = 0, c = 0, result = 0;
    std::sscanf(first.str(), "%u", &a);
    std::sscanf(second.str(), "%u", &b);
    std::sscanf(third.str(), "%u", &c);
    combined.appendFormat("%02d%02d%04d", int(b), int(a + 30), int(c));
    std::sscanf(combined.str(), "%08u", &result);
    std::cout << serial << ' ' << decimal.str() << ' ' << first.str() << ' '
              << second.str() << ' ' << third.str() << ' ' << combined.str()
              << ' ' << a << ' ' << b << ' ' << c << ' ' << result << '\n';
  }
}
