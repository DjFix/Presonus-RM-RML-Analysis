#include "presonus/avb/streams.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <zlib.h>

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

static std::uint32_t word(const unsigned char *data) {
  return static_cast<std::uint32_t>(data[0]) |
         (static_cast<std::uint32_t>(data[1]) << 8) |
         (static_cast<std::uint32_t>(data[2]) << 16) |
         (static_cast<std::uint32_t>(data[3]) << 24);
}

static unsigned long long wide(const unsigned char *data) {
  return word(data) | (static_cast<unsigned long long>(word(data + 4)) << 32);
}

static int signedWord(std::uint32_t value) {
  int result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}

int main(int argc, char **argv) {
  try {
    require(argc == 3, "client and server fixtures required");
    unsigned long count = 0;
    for (int file = 1; file < argc; ++file) {
      gzFile input = gzopen(argv[file], "rb");
      require(input != nullptr, "fixture open");
      std::array<unsigned char, 69> record{};
      for (;;) {
        const auto got = gzread(input, record.data(), record.size());
        if (got == 0)
          break;
        require(got == static_cast<int>(record.size()), "truncated fixture");
        const unsigned operation = record[0];
        const auto identifierByte =
            static_cast<unsigned char>(word(record.data() + 1));
        const auto identifier = wide(record.data() + 5);
        const auto suffix =
            static_cast<unsigned short>(word(record.data() + 13));
        const auto integerWord = signedWord(word(record.data() + 17));
        const auto first = static_cast<unsigned char>(word(record.data() + 21));
        const auto second =
            static_cast<unsigned char>(word(record.data() + 25));
        const auto third = static_cast<unsigned char>(word(record.data() + 29));
        const auto expectedResult = word(record.data() + 33);
        const auto *expected = record.data() + 37;
        require(operation < 10, "operation");
        if (operation < 5) {
          alignas(Presonus::AVB::AvbListener)
              std::array<unsigned char, sizeof(Presonus::AVB::AvbListener)>
                  storage;
          storage.fill(0xa5);
          auto *instance = new (storage.data()) Presonus::AVB::AvbListener(
              identifierByte, identifier, suffix, integerWord);
          const auto before = storage;
          if (operation == 4)
            require(static_cast<std::uint32_t>(instance->update(
                        first, second, third)) == expectedResult,
                    "listener update return");
          const auto state = instance->inspectState();
          require(state.identifierByte == expected[0] &&
                      state.identifier == wide(expected + 8) &&
                      state.streamKey == wide(expected + 16) &&
                      state.suffix == (word(expected + 24) & 0xffffU) &&
                      state.integerWord == signedWord(word(expected + 28)),
                  "listener state");
          require(storage == before, "listener update wrote storage");
          instance->~AvbListener();
          require(storage == before, "listener destructor wrote storage");
        } else {
          alignas(Presonus::AVB::AvbTalker)
              std::array<unsigned char, sizeof(Presonus::AVB::AvbTalker)>
                  storage;
          storage.fill(0xa5);
          auto *instance = new (storage.data())
              Presonus::AVB::AvbTalker(identifierByte, integerWord);
          const auto before = storage;
          if (operation == 9)
            require(static_cast<std::uint32_t>(
                        instance->update(first, second)) == expectedResult,
                    "talker update return");
          const auto state = instance->inspectState();
          require(state.identifierByte == expected[0] &&
                      state.integerWord == signedWord(word(expected + 8)),
                  "talker state");
          require(storage == before, "talker update wrote storage");
          instance->~AvbTalker();
          require(storage == before, "talker destructor wrote storage");
        }
        ++count;
      }
      require(gzclose(input) == Z_OK, "fixture close");
    }
    std::cout << "PASS " << count << " original ARM AVB stream fixtures\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
