#include "presonus/avb/protocol.hpp"
#include "presonus/dice/sysex.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <zlib.h>

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

static std::uint32_t readWord(gzFile file) {
  std::array<unsigned char, 4> data{};
  require(gzread(file, data.data(), data.size()) ==
              static_cast<int>(data.size()),
          "truncated word");
  return static_cast<std::uint32_t>(data[0]) |
         (static_cast<std::uint32_t>(data[1]) << 8) |
         (static_cast<std::uint32_t>(data[2]) << 16) |
         (static_cast<std::uint32_t>(data[3]) << 24);
}

int main(int argc, char **argv) {
  try {
    require(argc == 4, "accept, reverse and memory fixtures required");
    Presonus::AVB::AvbManagerBase manager;
    std::ifstream accepts(argv[1]);
    require(accepts.good(), "accept fixture open");
    unsigned length, command, expected;
    unsigned long acceptedCases = 0, reversedCases = 0, memoryCases = 0;
    Presonus::DICE::SysexPacket packet;
    packet.bytes.fill(0xa5);
    while (accepts >> std::hex >> length >> command >> expected) {
      packet.length = static_cast<unsigned char>(length);
      packet.bytes[1] = static_cast<unsigned char>(command);
      require(manager.accepts(packet) == static_cast<bool>(expected),
              "accept mismatch");
      ++acceptedCases;
    }
    require(accepts.eof(), "malformed accept fixture");
    std::ifstream reverse(argv[2]);
    require(reverse.good(), "reverse fixture open");
    unsigned long long value, result;
    while (reverse >> std::hex >> value >> result) {
      require(manager.reverseEndian(value) == result, "reverse mismatch");
      ++reversedCases;
    }
    require(reverse.eof(), "malformed reverse fixture");
    gzFile memory = gzopen(argv[3], "rb");
    require(memory != nullptr, "memory fixture open");
    for (;;) {
      unsigned char operation;
      const auto got = gzread(memory, &operation, 1);
      if (got == 0)
        break;
      require(got == 1, "memory fixture error");
      const auto lengthWord = readWord(memory);
      const auto sourceOffset = readWord(memory);
      const auto destinationOffset = readWord(memory);
      const auto expectedResult = readWord(memory);
      std::array<unsigned char, 512> arena{}, after{};
      require(gzread(memory, arena.data(), arena.size()) ==
                  static_cast<int>(arena.size()),
              "truncated initial arena");
      require(gzread(memory, after.data(), after.size()) ==
                  static_cast<int>(after.size()),
              "truncated expected arena");
      auto *source =
          sourceOffset == 0xffffffffU ? nullptr : arena.data() + sourceOffset;
      auto *destination = destinationOffset == 0xffffffffU
                              ? nullptr
                              : arena.data() + destinationOffset;
      int signedLength;
      std::memcpy(&signedLength, &lengthWord, sizeof signedLength);
      if (operation == 'C')
        manager.char2Nibble(source, destination, signedLength);
      else if (operation == 'N')
        manager.nibble2Char(source, destination, signedLength);
      else if (operation == 'U')
        require(static_cast<std::uint32_t>(manager.unpackAvbSpiMsg(
                    destination, source, signedLength)) == expectedResult,
                "SPI unpack status");
      else
        throw std::runtime_error("unknown operation");
      require(arena == after, "complete memory/alias/guard mismatch");
      ++memoryCases;
    }
    require(gzclose(memory) == Z_OK, "memory fixture close");
    std::cout << "PASS " << acceptedCases << " accepts, " << reversedCases
              << " reverse, " << memoryCases << " exact-memory ARM fixtures\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
