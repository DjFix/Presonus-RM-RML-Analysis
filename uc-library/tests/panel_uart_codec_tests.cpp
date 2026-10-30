#include "presonus/panel/uart_message.hpp"
#include <array>
#include <csetjmp>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>

static sigjmp_buf stop;
static volatile unsigned terminal;
extern "C" [[noreturn]] void
__wrap___assert_fail(const char *expression, const char *, unsigned line,
                     const char *function) noexcept {
  if (!std::strcmp(function, "EncodeLed") && line == 836 &&
      !std::strcmp(expression, "msg->Led.Group <= 15"))
    terminal = 1;
  else if (!std::strcmp(function, "EncodeSwitchUp") && line == 925 &&
           !std::strcmp(expression, "msg->SwitchDown.Group <= 15"))
    terminal = 2;
  else if (!std::strcmp(function, "EncodeSwitchDown") && line == 914 &&
           !std::strcmp(expression, "msg->SwitchDown.Group <= 15"))
    terminal = 3;
  else
    std::abort();
  siglongjmp(stop, 1);
}
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static void word(unsigned char *p, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    p[i] = static_cast<unsigned char>(n >> (8 * i));
}
static int integer(unsigned n) {
  int v;
  std::memcpy(&v, &n, 4);
  return v;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "UPRTv001", 8))
    return 3;
  unsigned count = word(header.data() + 8);
  for (unsigned index = 0; index < count; ++index) {
    std::array<unsigned char, 116> input{};
    std::array<unsigned char, 268> expected{}, actual{};
    f.read(reinterpret_cast<char *>(input.data()), input.size());
    f.read(reinterpret_cast<char *>(expected.data()), expected.size());
    if (!f)
      return 4;
    unsigned op = word(input.data()), a = word(input.data() + 4),
             b = word(input.data() + 8), c = word(input.data() + 12);
    static Uart_Msg_Type message;
    std::memcpy(message.bytes.data(), input.data() + 16, 4);
    static std::array<char, 96> data;
    std::memcpy(data.data(), input.data() + 20, 96);
    static std::array<char, 256> output;
    output.fill(static_cast<char>(0xcc));
    volatile std::uint32_t result = 0;
    terminal = 0;
    if (sigsetjmp(stop, 1) == 0) {
      if (op == 0)
        result = uart_protocol_encode(&message, output.data());
      else if (op == 1)
        result = uart_protocol_decode(data.data() + 2, a, &message);
      else if (op == 2)
        result = utils_Ascii2Int(data.data(), integer(a));
      else if (op == 3)
        result = utils_ConvertInt2Hex(a, b, output.data(), c);
      else
        return 5;
    }
    word(actual.data(), terminal);
    word(actual.data() + 4, terminal ? 0 : result);
    std::memcpy(actual.data() + 8, message.bytes.data(), 4);
    std::memcpy(actual.data() + 12, output.data(), 256);
    if (std::memcmp(actual.data(), expected.data(), expected.size())) {
      unsigned at = 0;
      while (at < actual.size() && actual[at] == expected[at])
        ++at;
      std::fprintf(stderr,
                   "codec fixture%u op%u a%u b%u c%u msg%02x%02x%02x%02x "
                   "byte%u got%u want%u\n",
                   index, op, a, b, c, input[16], input[17], input[18],
                   input[19], at, actual[at], expected[at]);
      return 6;
    }
  }
  std::printf("%u original ARM UART codec/helper fixtures passed; assertions "
              "terminal and no Core bodies\n",
              count);
}
