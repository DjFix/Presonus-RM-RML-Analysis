#include "presonus/dice/codec.hpp"
#include <array>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

std::array<unsigned char, 32> unhex(const std::string &text) {
  if (text.size() != 64)
    throw std::runtime_error("fixture buffer width");
  std::array<unsigned char, 32> result{};
  for (unsigned i = 0; i < 32; ++i)
    result[i] = static_cast<unsigned char>(
        std::stoul(text.substr(i * 2, 2), nullptr, 16));
  return result;
}
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::runtime_error("fixture path required");
    std::ifstream file(argv[1]);
    if (!file)
      throw std::runtime_error("fixture open failed");
    char op;
    unsigned int value, offset, expected;
    std::string before, after;
    std::map<char, unsigned> counts;
    while (file >> op >> std::hex >> value >> offset >> before >> expected >>
           after) {
      auto buffer = unhex(before);
      unsigned int result = 0;
      if (offset + 5 > buffer.size())
        throw std::runtime_error("fixture offset");
      switch (op) {
      case 'U':
        result = unpack32(buffer.data() + offset);
        break;
      case 'u':
        result = unpack16(buffer.data() + offset);
        break;
      case 'P':
        pack32(value, buffer.data() + offset);
        break;
      case 'p':
        pack16(static_cast<unsigned short>(value), buffer.data() + offset);
        break;
      default:
        throw std::runtime_error("unknown operation");
      }
      if (result != expected || buffer != unhex(after)) {
        std::cerr << op << " case=" << counts[op] << " expected=" << std::hex
                  << expected << " actual=" << result << '\n';
        throw std::runtime_error("original ARM return/buffer mismatch");
      }
      ++counts[op];
    }
    if (!file.eof() || counts.size() < 2)
      throw std::runtime_error("incomplete fixtures");
    std::cout << "PASS:";
    for (const auto &[op, count] : counts)
      std::cout << ' ' << op << '=' << std::dec << count;
    std::cout << " exact ARM unpack results and complete buffers; pack returns "
                 "excluded/pending\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
