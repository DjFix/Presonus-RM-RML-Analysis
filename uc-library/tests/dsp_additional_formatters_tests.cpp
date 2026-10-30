#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
int main(int argc, char **argv) {
  std::ifstream fixture;
  if (argc > 1)
    fixture.open(argv[1]);
  if (argc > 1 && !fixture)
    return 2;
  std::istream &inputStream =
      argc > 1 ? static_cast<std::istream &>(fixture) : std::cin;
  unsigned count = 0;
  bool exact = true;
  using namespace Presonus::Dsp;
  std::string cls, op, hex;
  std::uint32_t word, maxword;
  int option, flag, size;
  while (inputStream >> cls >> op >> word >> hex >> option >> flag >> size >>
         maxword) {
    unsigned expectedOk = 0, expectedWord = 0;
    std::string expectedText;
    if (argc > 1 &&
        !(inputStream >> expectedOk >> expectedWord >> expectedText))
      return 3;
    char buffer[512];
    std::memset(buffer, 0xa5, sizeof(buffer));
    std::string input;
    if (hex != "-")
      for (std::size_t i = 0; i < hex.size(); i += 2)
        input.push_back(
            static_cast<char>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    std::memcpy(buffer, input.c_str(), input.size() + 1);
    float value, maximum;
    std::memcpy(&value, &word, 4);
    std::memcpy(&maximum, &maxword, 4);
    Core::Formatter::Range range{0, maximum};
    Core::Formatter::Data data{nullptr, buffer, size, value, &range};
    BPMFormatter bpm(AdditionalFormatterSourceTag{}, option != 0);
    MillisecondsFormatter milliseconds(AdditionalFormatterSourceTag{},
                                       option != 0);
    CounterFormatter counter(AdditionalFormatterSourceTag{}, option);
    GainFormatter gain(AdditionalFormatterSourceTag{}, option, flag);
    PanFormatter pan(AdditionalFormatterSourceTag{}, option);
    Core::Formatter *formatter =
        cls == "BPM"            ? static_cast<Core::Formatter *>(&bpm)
        : cls == "Milliseconds" ? static_cast<Core::Formatter *>(&milliseconds)
        : cls == "Counter"      ? static_cast<Core::Formatter *>(&counter)
        : cls == "Gain"         ? static_cast<Core::Formatter *>(&gain)
                                : static_cast<Core::Formatter *>(&pan);
    bool ok = false;
    if (op == "print")
      formatter->print(data);
    else
      ok = formatter->scan(data);
    std::memcpy(&word, &data.value, 4);
    std::string encoded;
    const char digits[] = "0123456789abcdef";
    for (const unsigned char *p = reinterpret_cast<unsigned char *>(buffer); *p;
         ++p) {
      encoded += digits[*p >> 4];
      encoded += digits[*p & 15];
    }
    const auto output = encoded.empty() ? std::string("-") : encoded;
    if (argc > 1) {
      exact = exact && expectedOk == static_cast<unsigned>(ok) &&
              expectedWord == word && expectedText == output;
      ++count;
    } else
      std::cout << ok << ' ' << word << ' ' << output << std::endl;
  }
  if (argc > 1) {
    std::cout << "{\"exact\":" << (exact ? "true" : "false")
              << ",\"cases\":" << count << "}" << std::endl;
    return exact ? 0 : 1;
  }
}
