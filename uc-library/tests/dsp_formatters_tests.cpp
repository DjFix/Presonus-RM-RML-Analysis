#include "presonus/mixer_dsp/Formatters.hpp"
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
  int flag, size;
  while (inputStream >> cls >> op >> word >> hex >> flag >> size >> maxword) {
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
    TimeFormatter time(FormatterSourceTag{});
    FreqFormatter freq(FormatterSourceTag{}, flag);
    GainDBFormatter gain(FormatterSourceTag{}, flag);
    RatioFormatter ratio(FormatterSourceTag{});
    EQQFormatter eqq(FormatterSourceTag{});
    Core::Formatter *formatter =
        cls == "Time"     ? static_cast<Core::Formatter *>(&time)
        : cls == "Freq"   ? static_cast<Core::Formatter *>(&freq)
        : cls == "GainDB" ? static_cast<Core::Formatter *>(&gain)
        : cls == "Ratio"  ? static_cast<Core::Formatter *>(&ratio)
                          : static_cast<Core::Formatter *>(&eqq);
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
