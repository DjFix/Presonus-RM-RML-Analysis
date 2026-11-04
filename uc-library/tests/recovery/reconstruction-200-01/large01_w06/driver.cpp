#include "presonus/reconstruction200/large01_w06.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
namespace {
std::string hex(const void *p, std::size_t n) {
  auto *b = static_cast<const unsigned char *>(p);
  std::ostringstream out;
  for (std::size_t i = 0; i < n; ++i)
    out << std::hex << std::setfill('0') << std::setw(2) << unsigned(b[i]);
  return out.str();
}
void unhex(const std::string &s, void *p) {
  auto *b = static_cast<unsigned char *>(p);
  for (std::size_t i = 0; i < s.size() / 2; ++i)
    b[i] =
        static_cast<unsigned char>(std::stoul(s.substr(i * 2, 2), nullptr, 16));
}
void invoke(Presonus::DisplayCommandList &p, int idx, const int (&v)[4],
            const unsigned (&c)[4]) {
  Core::Color color(c[0], c[1], c[2], c[3]);
  Core::TRect<int> r(v[0], v[1], v[2], v[3]);
  switch (idx) {
  case 2:
    p.drawLine(v[0], v[1], v[2], v[3], color);
    break;
  case 3:
    p.fillRect(r, color);
    break;
  case 4:
    p.setClip(r);
    break;
  case 5:
    p.drawVerticalLine(v[0], v[1], v[2], color);
    break;
  case 6:
    p.flush();
    break;
  case 7:
    p.drawHorizontalLine(v[0], v[1], v[2], color);
    break;
  default:
    throw std::runtime_error("unknown operation");
  }
}
} // namespace
int main() {
  std::string kind;
  while (std::cin >> kind) {
    if (kind == "rect") {
      Core::TRect<int> r;
      std::cin >> r.left >> r.top >> r.right >> r.bottom;
      Presonus::SpectrumPainter p(r);
      auto result = p.getLastDrawnRect();
      std::cout << hex(&result, 16) << '\n';
    } else if (kind == "command") {
      int idx;
      Presonus::DisplayCommandList::State s;
      int v[4];
      unsigned c[4];
      std::string initial;
      std::cin >> idx >> s.count >> s.auxiliaryCursor;
      for (auto &x : v)
        std::cin >> x;
      for (auto &x : c)
        std::cin >> x;
      std::cin >> initial;
      unhex(initial, s.commands.data());
      Presonus::DisplayCommandList p(s);
      invoke(p, idx, v, c);
      std::cout << hex(s.commands.data(), 1000) << ' ' << s.count << ' '
                << s.auxiliaryCursor << '\n';
    } else if (kind == "sequence") {
      Presonus::DisplayCommandList::State s;
      unsigned n;
      std::string initial;
      std::cin >> s.count >> s.auxiliaryCursor >> initial >> n;
      unhex(initial, s.commands.data());
      Presonus::DisplayCommandList p(s);
      for (unsigned i = 0; i < n; ++i) {
        int idx, v[4];
        unsigned c[4];
        std::cin >> idx;
        for (auto &x : v)
          std::cin >> x;
        for (auto &x : c)
          std::cin >> x;
        invoke(p, idx, v, c);
      }
      std::cout << hex(s.commands.data(), 1000) << ' ' << s.count << ' '
                << s.auxiliaryCursor << '\n';
    } else if (kind == "map") {
      int index;
      unsigned c[4];
      std::cin >> index;
      for (auto &x : c)
        std::cin >> x;
      Core::Color color(c[0], c[1], c[2], c[3]);
      if (index == 10) {
        const char *p = Presonus::ColorMapping::mapColor(color);
        std::cout << (p ? p : "<null>") << '\n';
      } else
        std::cout << Presonus::ColorMapping::mapColorToEnum(color) << '\n';
    } else if (kind == "diff") {
      Presonus::ColorMapping::Item a{}, b{};
      std::cin >> a.hue >> a.saturation >> a.lightness >> a.alpha >> b.hue >>
          b.saturation >> b.lightness >> b.alpha;
      float result = Presonus::ColorMapping::getDiff(a, b);
      std::uint32_t bits;
      std::memcpy(&bits, &result, 4);
      std::cout << bits << '\n';
    } else {
      return 3;
    }
  }
}
