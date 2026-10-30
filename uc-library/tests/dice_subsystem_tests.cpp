#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

using Presonus::DICE::Dice3Subsystem;
using Presonus::DICE::SysexPacket;

static void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}
static std::string unhex(const std::string &text) {
  require(text.size() % 2 == 0, "odd fixture hex length");
  std::string result;
  for (std::size_t i = 0; i < text.size(); i += 2)
    result.push_back(
        static_cast<char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return result;
}

int main(int argc, char **argv) {
  try {
    require(argc == 2, "ARM fixture path required");
    std::ifstream input(argv[1]);
    require(bool(input), "missing fixture file");
    SysexPacket packet, other;
    Dice3Subsystem subsystem(presonus::dice::BorrowedSubsystemSetup{});
    const char *shared = nullptr;
    std::map<std::string, const char *> pointers;
    char operation;
    unsigned accepts_count = 0, string_count = 0;
    while (input >> operation) {
      if (operation == 'A') {
        unsigned length, command, expected;
        require(bool(input >> length >> command >> expected),
                "invalid filter fixture");
        packet.length = static_cast<unsigned char>(length);
        packet.bytes[1] = static_cast<unsigned char>(command);
        require(subsystem.accepts(packet) == bool(expected),
                "filter mismatch: length=" + std::to_string(length) +
                    " command=" + std::to_string(command));
        ++accepts_count;
      } else {
        require(operation == 'G', "unknown fixture operation");
        unsigned command;
        std::string expected, group, shared_value;
        require(bool(input >> command >> expected >> group >> shared_value),
                "invalid string fixture");
        auto result =
            (string_count % 2 ? other : packet)
                .getSysexCommandStr(static_cast<unsigned char>(command));
        require(std::string(result) == unhex(expected),
                "command string mismatch: " + std::to_string(command));
        const auto prior = pointers.find(group);
        if (prior == pointers.end())
          pointers[group] = result;
        else
          require(result == prior->second,
                  "return pointer identity changed: " + group);
        if (group == "U") {
          if (shared)
            require(result == shared,
                    "unknown buffer is not shared across instances");
          shared = result;
        }
        if (shared)
          require(std::string(shared) == unhex(shared_value),
                  "retained unknown pointer did not observe original buffer "
                  "mutation behavior");
        ++string_count;
      }
    }
    require(accepts_count == 65536,
            "missing exhaustive command/length coverage");
    require(string_count >= 256, "missing exhaustive command string coverage");
    std::cout << "PASS: " << accepts_count << " original ARM filter cases, "
              << string_count
              << " command-string cases; shared-buffer aliasing and "
                 "cross-instance mutation checked\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
