#include "presonus/uc/DicePacketQueue.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

using Presonus::UC::DicePacketQueue;
using Presonus::UC::Packet;
void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}
template <std::size_t N>
std::array<unsigned char, N> unhex(const std::string &text) {
  require(text.size() == N * 2, "invalid fixture length");
  std::array<unsigned char, N> result{};
  for (std::size_t i = 0; i < N; ++i)
    result[i] = static_cast<unsigned char>(
        std::stoul(text.substr(i * 2, 2), nullptr, 16));
  return result;
}
int main(int argc, char **argv) {
  try {
    require(argc == 2, "ARM vector path required");
    std::ifstream input(argv[1]);
    require(bool(input), "missing ARM vectors");
    char operation;
    std::string id;
    unsigned encoded = 0, decoded = 0;
    while (input >> operation >> id) {
      Packet packet;
      std::string storage, midi_text, expected_text;
      int success;
      std::int32_t size, expected_size;
      unsigned output_length, expected_length;
      if (operation == 'E') {
        require(bool(input >> size >> storage >> midi_text >> output_length >>
                     success >> expected_length >> expected_text),
                "malformed encode fixture");
        packet.bytes = unhex<200>(storage);
        packet.length = size;
        auto midi = unhex<255>(midi_text);
        auto length = static_cast<unsigned char>(output_length);
        require(DicePacketQueue::toMIDI(packet, midi.data(), length) ==
                    bool(success),
                id + ": encode return");
        require(length == expected_length, id + ": encode length");
        require(midi == unhex<255>(expected_text),
                id + ": encode bytes / untouched suffix");
        require(packet.bytes == unhex<200>(storage) && packet.length == size,
                id + ": encoder changed input packet");
        ++encoded;
      } else {
        require(operation == 'D', "unknown operation");
        require(bool(input >> midi_text >> storage >> size >> success >>
                     expected_size >> expected_text),
                "malformed decode fixture");
        packet.bytes = unhex<200>(storage);
        packet.length = size;
        auto midi = unhex<255>(midi_text);
        require(DicePacketQueue::fromMIDI(packet, midi.data()) == bool(success),
                id + ": decode return");
        require(packet.length == expected_size, id + ": decode length");
        require(packet.bytes == unhex<200>(expected_text),
                id + ": decoded bytes / untouched suffix");
        require(midi == unhex<255>(midi_text),
                id + ": decoder changed MIDI input");
        ++decoded;
      }
    }
    require(encoded > 0 && decoded > 0, "incomplete fixtures");
    for (int length = 1; length <= 200; ++length) {
      Packet original, restored;
      original.length = length;
      for (unsigned i = 0; i < 200; ++i)
        original.bytes[i] = static_cast<unsigned char>(i * 37 + length);
      std::array<unsigned char, 255> midi{};
      unsigned char count = 0;
      require(DicePacketQueue::toMIDI(original, midi.data(), count),
              "roundtrip encode");
      require(DicePacketQueue::fromMIDI(restored, midi.data()),
              "roundtrip decode");
      require(restored.length == length &&
                  std::equal(original.bytes.begin(),
                             original.bytes.begin() + length,
                             restored.bytes.begin()),
              "valid packet roundtrip");
    }
    std::cout << "PASS: " << encoded << " ARM encode fixtures, " << decoded
              << " ARM decode fixtures, 200 valid-length roundtrips\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
