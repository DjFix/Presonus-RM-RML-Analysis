#include "presonus/dice/programmer.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

template <typename T> static T *pointer(std::uint32_t word) {
  return reinterpret_cast<T *>(static_cast<std::uintptr_t>(word));
}

static std::uint32_t bits(float value) {
  std::uint32_t word;
  std::memcpy(&word, &value, 4);
  return word;
}

static float asFloat(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, 4);
  return value;
}

class Recorder : public presonus::dice::ProgressSink {
public:
  unsigned calls = 0;
  Presonus::UC::IFirmwareUpdateListener *listener = nullptr;
  const char *text = nullptr;
  std::uint32_t value = 0;
  void report(Presonus::UC::IFirmwareUpdateListener *receiver,
              const char *label, float level) override {
    ++calls;
    listener = receiver;
    text = label;
    value = bits(level);
  }
};

int main(int argc, char **argv) {
  try {
    require(argc == 2, "fixture path required");
    std::ifstream input(argv[1]);
    require(input.good(), "fixture open failed");
    std::string operation;
    std::uint32_t listenerWord, imageWord, length, textWord, floatWord, force,
        expectedCalls, expectedResult;
    unsigned long count = 0;
    while (input >> operation >> std::hex >> listenerWord >> imageWord >>
           length >> textWord >> floatWord >> force >> expectedCalls >>
           expectedResult) {
      auto *listener =
          pointer<Presonus::UC::IFirmwareUpdateListener>(listenerWord);
      auto *image = pointer<const unsigned char>(imageWord);
      alignas(Presonus::DICE::Dice3Programmer)
          std::array<unsigned char, sizeof(Presonus::DICE::Dice3Programmer)>
              storage;
      storage.fill(0xa5);
      auto *instance = new (storage.data())
          Presonus::DICE::Dice3Programmer(listener, image, length);
      const auto state = instance->inspectState();
      require(state.descriptor == -1 && state.image == image &&
                  state.length == length && state.listener == listener,
              "constructor state");
      Recorder recorder;
      instance->bindProgressSink(recorder);
      const auto before = storage;
      if (operation == "V")
        require(static_cast<std::uint32_t>(instance->verify()) ==
                    expectedResult,
                "verify return");
      else if (operation == "P") {
        instance->printProgress(pointer<const char>(textWord),
                                asFloat(floatWord), force != 0);
        require(recorder.calls == expectedCalls, "progress call count");
        if (expectedCalls)
          require(recorder.listener == listener &&
                      recorder.text == pointer<const char>(textWord) &&
                      recorder.value == floatWord,
                  "progress exact payload");
      } else
        require(operation == "C1" || operation == "C2" || operation == "D1" ||
                    operation == "D2",
                "operation");
      require(before == storage, "method changed programmer state");
      instance->~Dice3Programmer();
      require(before == storage, "destructor changed storage");
      ++count;
    }
    require(input.eof(), "malformed fixture");
    std::cout << "PASS " << count << " original ARM programmer fixtures\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
