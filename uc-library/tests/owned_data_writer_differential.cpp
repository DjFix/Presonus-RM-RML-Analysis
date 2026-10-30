#include "presonus/uc/owned_data_factory_codec.hpp"
#include <fstream>
#include <iostream>
#include <vector>
using namespace presonus::uc;
using namespace Presonus::UC;
namespace {
unsigned readWord(std::istream &input) {
  unsigned char b[4];
  if (!input.read(reinterpret_cast<char *>(b), 4))
    throw std::runtime_error("short writer fixture");
  return unsigned(b[0]) | (unsigned(b[1]) << 8) | (unsigned(b[2]) << 16) |
         (unsigned(b[3]) << 24);
}
template <class Codec>
void replay(unsigned length, unsigned capacity, unsigned result,
            unsigned cursor, const std::vector<unsigned char> &expected) {
  Codec codec;
  typename Codec::value_type value{};
  std::vector<unsigned char> data(length);
  for (unsigned n = 0; n < length; ++n)
    data[n] = static_cast<unsigned char>(n * 73 + 17);
  value.header = {unsigned(Codec::type), 0xdeadbeef, 0x12345, 0xabcde};
  value.data = data.empty() ? nullptr : data.data();
  value.sizeBits = length;
  if constexpr (Codec::payload_words > 0)
    value.word24 = 0x81234567;
  if constexpr (Codec::payload_words > 1) {
    value.word28 = 0xdeadbeef;
    value.word32 = 0x7f812345;
  }
  codec.bind(value);
  std::vector<unsigned char> actual(capacity + 16, 0xa5);
  BufferWriter writer(actual.data() + 8, capacity);
  const auto &callbacks = codec.codec();
  const bool returned =
      callbacks.write(callbacks.context, writer, value.header);
  if (unsigned(returned) != result || unsigned(writer.position()) != cursor ||
      actual != expected)
    throw std::runtime_error("original ARM writer differential mismatch");
  codec.unbind(value);
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1], std::ios::binary);
  char magic[4];
  if (!input.read(magic, 4) || std::string(magic, 4) != "ODW1")
    return 3;
  const auto count = readWord(input);
  for (unsigned n = 0; n < count; ++n) {
    const auto type = readWord(input), length = readWord(input),
               capacity = readWord(input), result = readWord(input),
               cursor = readWord(input), bytes = readWord(input);
    if (bytes != capacity + 16 || bytes > 512 || length > 255)
      return 4;
    std::vector<unsigned char> expected(bytes);
    if (!input.read(reinterpret_cast<char *>(expected.data()), bytes))
      return 5;
#define RUN(code, ...)                                                         \
  case code:                                                                   \
    replay<__VA_ARGS__>(length, capacity, result, cursor, expected);           \
    break
    switch (type) {
      RUN(16975, BinaryFactoryCodec);
      RUN(17227, MessageChunkFactoryCodec);
      RUN(23117, EncodedDataFactoryCodec<23117>);
      RUN(19021, EncodedDataFactoryCodec<19021>);
      RUN(21826, EncodedDataFactoryCodec<21826>);
      RUN(23106, EncodedDataFactoryCodec<23106>);
      RUN(19537, LoopbackQueryDataFactoryCodec);
      RUN(19538, LoopbackReplyDataFactoryCodec);
      RUN(21324, MidiLongSysexDataFactoryCodec);
    default:
      return 6;
    }
#undef RUN
  }
  if (input.peek() != std::char_traits<char>::eof())
    return 7;
  std::cout << "original app ARM writer differential PASS " << count
            << " cases; exact return/cursor/guarded partial bytes\n";
}
