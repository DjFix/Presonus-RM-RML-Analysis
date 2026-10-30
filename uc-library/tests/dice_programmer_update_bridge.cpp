#include "presonus/dice/programmer.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {
void require(bool value) {
  if (!value)
    std::abort();
}
std::int32_t signedWord(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
std::string hex(const unsigned char *data, std::size_t count) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (std::size_t i = 0; i < count; ++i) {
    result += digits[data[i] >> 4];
    result += digits[data[i] & 15];
  }
  return result;
}
std::vector<unsigned char> unhex(const std::string &text) {
  std::vector<unsigned char> result;
  for (std::size_t i = 0; i < text.size(); i += 2)
    result.push_back(std::stoul(text.substr(i, 2), nullptr, 16));
  return result;
}
struct Case {
  unsigned kind;
  std::uint32_t sector, length, initial, enabled, transaction, final;
  int eraseAt, writeAt, verifyAt;
  std::uint32_t eraseError, writeError, verifyError;
};
Case current{};
Presonus::DICE::Dice3Programmer *object = nullptr;
const unsigned char *imageBase = nullptr;
unsigned waitIndex = 0;
std::vector<std::string> events;
class Runtime final : public presonus::dice::ProgrammerServices {
public:
  std::int32_t transfer(std::int32_t,
                        const presonus::dice::ProgrammerTransfer &) override {
    std::abort();
  }
  std::int64_t clockRawTicks() override { std::abort(); }
  void sleepMilliseconds(std::uint32_t value) override {
    require(value == 500);
    events.push_back("{\"kind\":\"sleep\",\"milliseconds\":500}");
  }
};
void pageEvent(const char *kind, int page, const unsigned char *data,
               int length) {
  const auto offset = data - imageBase;
  require(offset >= 0 && offset + length <= 4096 && length >= 0);
  events.push_back(std::string("{\"kind\":\"") + kind +
                   "\",\"page\":" + std::to_string(page) +
                   ",\"offset\":" + std::to_string(offset) +
                   ",\"length\":" + std::to_string(length) + ",\"data\":\"" +
                   hex(data, length) + "\"}");
}
} // namespace

extern "C" std::int32_t __wrap__ZN8Presonus4DICE15Dice3Programmer8busyWaitEi(
    Presonus::DICE::Dice3Programmer *self, int timeout) {
  require(self == object);
  events.push_back("{\"kind\":\"wait\",\"timeout\":" + std::to_string(timeout) +
                   "}");
  return signedWord(waitIndex++ == 0 ? current.initial : current.final);
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer11writeEnableEv(
    Presonus::DICE::Dice3Programmer *self) {
  require(self == object);
  events.push_back("{\"kind\":\"enable\"}");
  return signedWord(current.enabled);
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer18performTransactionENS1_15mp25TransactionE(
    Presonus::DICE::Dice3Programmer *self,
    Presonus::DICE::Dice3Programmer::mp25Transaction transaction) {
  require(self == object && transaction.portableReceiveLength == 0);
  events.push_back(
      "{\"kind\":\"transaction\",\"transmit\":\"" +
      hex(transaction.portableTransmit, transaction.portableTransmitLength) +
      "\",\"txlen\":" + std::to_string(transaction.portableTransmitLength) +
      ",\"rxlen\":0}");
  return signedWord(current.transaction);
}
extern "C" std::int32_t
__real__ZN8Presonus4DICE15Dice3Programmer11eraseSectorEi(
    Presonus::DICE::Dice3Programmer *, int);
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer11eraseSectorEi(
    Presonus::DICE::Dice3Programmer *self, int sector) {
  require(self == object);
  if (current.kind != 2)
    return __real__ZN8Presonus4DICE15Dice3Programmer11eraseSectorEi(self,
                                                                    sector);
  events.push_back(
      "{\"kind\":\"erase_sector\",\"sector\":" + std::to_string(sector) + "}");
  return sector == current.eraseAt ? signedWord(current.eraseError) : 0;
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer9writePageEiPKhi(
    Presonus::DICE::Dice3Programmer *self, int page, const unsigned char *data,
    int length) {
  require(self == object);
  pageEvent("write_page", page, data, length);
  return page == current.writeAt ? signedWord(current.writeError) : 0;
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer10verifyPageEiPKhi(
    Presonus::DICE::Dice3Programmer *self, int page, const unsigned char *data,
    int length) {
  require(self == object);
  pageEvent("verify_page", page, data, length);
  return page == current.verifyAt ? signedWord(current.verifyError) : 0;
}
extern "C" void __real__ZN8Presonus4DICE15Dice3Programmer13printProgressEPKcfb(
    Presonus::DICE::Dice3Programmer *, const char *, float, bool);
extern "C" void __wrap__ZN8Presonus4DICE15Dice3Programmer13printProgressEPKcfb(
    Presonus::DICE::Dice3Programmer *self, const char *text, float value,
    bool force) {
  require(self == object);
  std::uint32_t bits;
  std::memcpy(&bits, &value, 4);
  events.push_back("{\"kind\":\"progress\",\"text\":\"" + std::string(text) +
                   "\",\"value_bits\":" + std::to_string(bits) +
                   ",\"force\":" + (force ? "true" : "false") + "}");
  __real__ZN8Presonus4DICE15Dice3Programmer13printProgressEPKcfb(self, text,
                                                                 value, force);
}

int main() {
  while (std::cin >> current.kind) {
    std::string imageHex;
    std::cin >> current.sector >> current.length >> current.initial >>
        current.enabled >> current.transaction >> current.final >>
        current.eraseAt >> current.eraseError >> current.writeAt >>
        current.writeError >> current.verifyAt >> current.verifyError >>
        imageHex;
    require(bool(std::cin));
    const auto image = unhex(imageHex);
    require(image.size() == 4096);
    imageBase = image.data();
    events.clear();
    waitIndex = 0;
    Runtime runtime;
    Presonus::DICE::Dice3Programmer instance(nullptr, image.data(),
                                             current.length);
    object = &instance;
    instance.bindProgrammerServices(runtime, 7);
    const auto before = instance.inspectState();
    std::int32_t result;
    if (current.kind == 0)
      result = instance.eraseAll();
    else if (current.kind == 1)
      result = instance.eraseSector(signedWord(current.sector));
    else {
      require(current.kind == 2);
      result = instance.update();
    }
    const auto after = instance.inspectState();
    require(before.descriptor == after.descriptor &&
            before.image == after.image && before.length == after.length &&
            before.listener == after.listener);
    require(hex(image.data(), image.size()) == imageHex);
    std::cout << "{\"return_word\":" << static_cast<std::uint32_t>(result)
              << ",\"events\":[";
    for (unsigned i = 0; i < events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << events[i];
    }
    std::cout << "]}\n";
    object = nullptr;
  }
  require(std::cin.eof());
}
