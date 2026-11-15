#include "presonus/surface/PageParam.hpp"
#include <cassert>
#include <iostream>
#include <string>
std::string decode(const std::string &s) {
  if (s == "-" || s == "e")
    return {};
  std::string out;
  for (std::size_t i = 0; i < s.size(); i += 2)
    out.push_back(static_cast<char>(std::stoi(s.substr(i, 2), nullptr, 16)));
  return out;
}
std::string hex(const char *p) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (; *p; ++p) {
    auto b = static_cast<unsigned char>(*p);
    out += digits[b >> 4];
    out += digits[b & 15];
  }
  return out;
}
int main() {
  std::string a, b;
  while (std::cin >> a >> b) {
    auto page = decode(a), parameter = decode(b);
    Presonus::Surface::PageParam value(a == "-" ? nullptr : page.c_str(),
                                       b == "-" ? nullptr : parameter.c_str());
    std::cout << hex(value.c_str()) << '\n';
    // Existing independent initialization/append API stays functional.
    Presonus::Surface::PageParam existing("seed:");
    existing.init("A", "B");
    assert(std::string(existing.c_str()) == "seed:page:A.B");
  }
}
