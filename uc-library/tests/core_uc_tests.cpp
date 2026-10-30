#include "presonus/core_uc/buffer.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

using Presonus::UC::BufferReader;
using Presonus::UC::BufferWriter;
void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}
std::uint32_t u32(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
std::int32_t i32(const unsigned char *p) {
  auto n = u32(p);
  return static_cast<std::int32_t>(
      n & 0x80000000u ? std::int64_t(n) - 0x100000000LL : n);
}
int main(int argc, char **argv) {
  try {
    require(argc == 2, "fixture path required");
    std::ifstream input(argv[1], std::ios::binary);
    require(bool(input), "missing fixtures");
    std::array<unsigned char, 12> header{};
    input.read(reinterpret_cast<char *>(header.data()), header.size());
    require(input.gcount() == 12 &&
                std::memcmp(header.data(), "UCBFv001", 8) == 0,
            "invalid vector header");
    const auto count = u32(header.data() + 8);
    std::array<std::uint32_t, 14> cases{};
    for (std::uint32_t index = 0; index < count; ++index) {
      std::array<unsigned char, 280> record{};
      input.read(reinterpret_cast<char *>(record.data()), record.size());
      require(input.gcount() == 280, "truncated fixture");
      const auto role = record[0], operation = record[1];
      require(role < 2 && operation < 7, "bad role/operation");
      const bool null = record[2] != 0, expected = record[3] != 0;
      const int capacity = i32(record.data() + 4),
                offset = i32(record.data() + 8), arg1 = i32(record.data() + 12),
                arg2 = i32(record.data() + 16), next = i32(record.data() + 20);
      std::array<unsigned char, 64> io{}, aux{};
      std::memcpy(io.data(), record.data() + 24, 64);
      std::memcpy(aux.data(), record.data() + 88, 64);
      BufferReader reader(io.data(), capacity, offset);
      BufferWriter writer(io.data(), capacity, offset);
      bool returned = false;
      int cursor = -1;
      switch (operation) {
      case 0:
        returned = reader.readRaw(aux.data(), arg1);
        cursor = reader.position();
        break;
      case 1:
        returned = reader.readRaw(aux.data(), arg1, arg2);
        cursor = reader.position();
        break;
      case 2:
        returned =
            reader.readCString(reinterpret_cast<char *>(aux.data()), arg1);
        cursor = reader.position();
        break;
      case 3: {
        unsigned short value =
            static_cast<unsigned short>(aux[0] | (unsigned(aux[1]) << 8));
        returned = reader.read<unsigned short>(value);
        aux[0] = static_cast<unsigned char>(value);
        aux[1] = static_cast<unsigned char>(value >> 8);
        cursor = reader.position();
        break;
      }
      case 4:
        returned = writer.writeRaw(aux.data(), arg1);
        cursor = writer.position();
        break;
      case 5:
        returned = writer.writeCString(
            null ? nullptr : reinterpret_cast<const char *>(aux.data()));
        cursor = writer.position();
        break;
      case 6:
        returned =
            writer.write<unsigned short>(static_cast<unsigned short>(arg1));
        cursor = writer.position();
        break;
      }
      const auto identity = "case " + std::to_string(index) + " role " +
                            std::to_string(role) + " operation " +
                            std::to_string(operation);
      require(returned == expected, identity + ": return mismatch");
      require(cursor == next, identity + ": cursor mismatch");
      require(reader.capacity() == capacity && writer.capacity() == capacity,
              identity + ": capacity changed");
      require(std::memcmp(io.data(), record.data() + 152, 64) == 0,
              identity + ": IO bytes mismatch");
      require(std::memcmp(aux.data(), record.data() + 216, 64) == 0,
              identity + ": output bytes mismatch");
      ++cases[role * 7 + operation];
    }
    require(input.peek() == std::char_traits<char>::eof(),
            "trailing vector bytes");
    for (auto n : cases)
      require(n > 0, "uncovered role/method");
    std::cout << "PASS: " << count
              << " original-ARM fixtures across seven methods in both ELFs; "
                 "return/cursor/buffer bytes match\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
