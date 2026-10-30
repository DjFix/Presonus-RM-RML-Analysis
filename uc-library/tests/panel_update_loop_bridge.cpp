#include "presonus/mcu/update_loop.hpp"
#include <array>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace presonus::mcu::panel;
struct Script {
  unsigned fallback = 0x1b;
  std::vector<unsigned> queries;
  std::vector<std::int32_t> transfers;
  std::size_t q = 0, t = 0;
};
class Boundary final : public UpdateBoundary {
public:
  std::array<Script, 5> scripts;
  std::vector<std::string> events;
  std::uint32_t image_crc = 0;
  unsigned index(std::uint8_t target) {
    constexpr std::array<unsigned, 5> targets{0x61, 0x60, 0x69, 0x68, 0x6f};
    for (unsigned i = 0; i < targets.size(); ++i)
      if (targets[i] == target)
        return i;
    throw std::runtime_error("unexpected target");
  }
  void event(const std::string &value) {
    events.push_back(value + ":" + std::to_string(interrupts_masked));
  }
  void delay(std::uint32_t count) override {
    event("D:" + std::to_string(count));
  }
  std::uint8_t query(std::uint8_t target) override {
    auto &s = scripts[index(target)];
    auto value = s.q < s.queries.size() ? s.queries[s.q++] : s.fallback;
    event("Q:" + std::to_string(target) + ":" + std::to_string(value));
    return value;
  }
  void control(std::uint8_t target) override {
    event("C:" + std::to_string(target));
  }
  std::int32_t transfer(std::uint8_t target, std::uint32_t pointer,
                        std::uint32_t length, std::uint8_t tag) override {
    auto &s = scripts[index(target)];
    auto value = s.t < s.transfers.size() ? s.transfers[s.t++] : 0;
    // Reuse the frozen, independently validated packet helper implementation.
    auto header = update_header(tag, length, image_crc);
    constexpr std::array<std::uint8_t, 14> expected{
        0, 0x27, 9, 0x1b, 0x70, 0x2f, 0, 0, 0xdc, 0x26, 0x90, 0x2a, 0xa8, 0xfb};
    if (pointer != 0x9e40 || header != expected)
      throw std::runtime_error("helper binding mismatch");
    event("T:" + std::to_string(target) + ":" + std::to_string(pointer) + ":" +
          std::to_string(length) + ":" + std::to_string(tag) + ":" +
          std::to_string(value));
    return value;
  }
  void status(std::uint32_t i, std::uint8_t code, std::uint8_t value) override {
    event("S:" + std::to_string(i) + ":" + std::to_string(code) + ":" +
          std::to_string(value));
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream stream(argv[1], std::ios::binary);
  std::vector<std::uint8_t> image((std::istreambuf_iterator<char>(stream)), {});
  if (image.size() != 53364)
    return 3;
  auto crc = crc32(image.data() + 0x9e40, 0x2f70);
  if (crc != 0x2a9026dc)
    return 4;
  for (std::string line; std::getline(std::cin, line);) {
    if (line == "quit") {
      std::cout << "OK\n" << std::flush;
      break;
    }
    std::istringstream in(line);
    unsigned flag, mask;
    in >> flag >> mask;
    Boundary io;
    io.image_crc = crc;
    io.interrupts_masked = mask != 0;
    for (auto &s : io.scripts) {
      unsigned nq, nt;
      in >> s.fallback >> nq;
      s.queries.resize(nq);
      for (auto &q : s.queries)
        in >> q;
      in >> nt;
      s.transfers.resize(nt);
      for (auto &t : s.transfers)
        in >> t;
    }
    if (!in)
      return 5;
    auto outcome = run_update_loop(io, static_cast<std::uint8_t>(flag));
    std::cout << outcome.return_value << ' ' << unsigned(outcome.final_flag)
              << ' ' << outcome.flag_written << ' ' << io.interrupts_masked
              << " |";
    for (std::size_t i = 0; i < io.events.size(); ++i) {
      if (i)
        std::cout << ';';
      std::cout << io.events[i];
    }
    std::cout << '\n' << std::flush;
  }
}
