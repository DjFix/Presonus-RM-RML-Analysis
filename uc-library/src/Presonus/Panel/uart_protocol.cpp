#include "presonus/panel/uart_message.hpp"
#include <cstddef>

extern "C" [[noreturn]] void __assert_fail(const char *, const char *, unsigned,
                                           const char *) noexcept;

extern "C" std::uint32_t utils_Ascii2Int(const char *text, int count) {
  std::uint32_t result = 0;
  for (int i = count; i > 0; --i) {
    const auto c = static_cast<unsigned char>(text[i - 1]);
    unsigned digit;
    if (c >= '0' && c <= '9')
      digit = c - '0';
    else if (c >= 'A' && c <= 'F')
      digit = c - 'A' + 10;
    else if (c >= 'a' && c <= 'f')
      digit = c - 'a' + 10;
    else
      continue;
    // ARM register shifts use their low8 bits; amounts>=32 produce zero.
    const unsigned shift = (std::uint32_t(count - i) * 4) & 255;
    if (shift < 32)
      result += std::uint32_t(digit) << shift;
  }
  return result;
}
extern "C" std::uint32_t utils_ConvertInt2Hex(std::uint32_t value,
                                              std::uint32_t upper, char *out,
                                              std::uint32_t digits) {
  if (digits == 0)
    return value; // Original register result retained, type pending.
  unsigned counter = (digits - 1) & 255;
  std::uint32_t written = 0;
  for (;;) {
    const unsigned shift = (counter * 4) & 255;
    const unsigned nibble = shift < 32 ? (value >> shift) & 15 : 0;
    out[written++] = static_cast<char>(nibble + (nibble <= 9 ? '0'
                                                 : upper     ? 'A' - 10
                                                             : 'a' - 10));
    if (counter == 0)
      break;
    counter = (counter - 1) & 255;
  }
  return written;
}
namespace {
std::uint16_t word(const Uart_Msg_Type &v) {
  return std::uint16_t(v.bytes[2]) | (std::uint16_t(v.bytes[3]) << 8);
}
void word(Uart_Msg_Type &v, std::uint32_t w) {
  v.bytes[2] = static_cast<std::uint8_t>(w);
  v.bytes[3] = static_cast<std::uint8_t>(w >> 8);
}
void groupAssertion(const char *expression, unsigned line,
                    const char *function) {
  // Original libc assertion boundary/strings; fixtures intercept this terminal
  // call without claiming normal-return or subsequent cleanup equivalence.
  __assert_fail(
      expression,
      "/var/lib/jenkins/workspace/cs18/trunk/rtkit/panel/base/uartprotocol.c",
      line, function);
}
} // namespace
extern "C" int uart_protocol_encode(const Uart_Msg_Type *message, char *out) {
  const auto &v = *message;
  const unsigned op = v.bytes[0];
  unsigned at = 0;
  auto hex = [&](unsigned value, unsigned digits) {
    utils_ConvertInt2Hex(value, 1, out + at, digits);
    at += digits;
  };
  auto finish = [&]() {
    out[at++] = static_cast<char>(op);
    return static_cast<int>(at);
  };
  switch (op) {
  case 'G':
  case 'g':
    hex(v.bytes[1], 1);
    hex(word(v), 3);
    break;
  case 'H':
  case 'v':
    hex(v.bytes[1], 2);
    break;
  case 'K':
    hex(v.bytes[1], 2);
    hex(word(v), 4);
    break;
  case 'L':
    if (v.bytes[1] > 15)
      groupAssertion("msg->Led.Group <= 15", 836, "EncodeLed");
    hex(v.bytes[1], 1);
    hex(v.bytes[2], 2);
    hex(v.bytes[3], 1);
    break;
  case 'M':
    hex(v.bytes[1], 2);
    hex(v.bytes[2], 1);
    break;
  case 'N':
  case 'O':
    hex(v.bytes[1], 2);
    hex(v.bytes[2], 1);
    hex(v.bytes[3], 1);
    break;
  case 'P':
  case 'x':
    hex(v.bytes[1], 1);
    hex(v.bytes[2], 2);
    break;
  case 'R':
    hex(v.bytes[1], 1);
    hex(word(v), 2);
    break;
  case 'S':
  case 's':
    if (v.bytes[1] > 15)
      groupAssertion("msg->SwitchDown.Group <= 15", op == 'S' ? 925 : 914,
                     op == 'S' ? "EncodeSwitchUp" : "EncodeSwitchDown");
    hex(v.bytes[1], 1);
    hex(v.bytes[2], 2);
    break;
  case 'T':
  case 'U':
  case 'z': {
    unsigned flags = v.bytes[3];
    hex(flags >> 4, 1);
    hex(((flags * 64) & 0x300) + v.bytes[1], 3);
    hex(((flags * 256) & 0x300) + v.bytes[2], 3);
    break;
  }
  case 'V':
    hex(v.bytes[1], 2);
    hex(v.bytes[2], 2);
    hex(v.bytes[3], 1);
    break;
  case 'b':
    hex(v.bytes[1], 1);
    hex(word(v), 4);
    break;
  case 'd':
  case 'm':
    hex(v.bytes[1], 2);
    hex(v.bytes[2], 2);
    break;
  case 'e': {
    const unsigned w = word(v);
    const int value =
        w >= 0x8000 ? static_cast<int>(w) - 0x10000 : static_cast<int>(w);
    hex(v.bytes[1], 2);
    out[at++] = value >= 0 ? '1' : '0';
    hex(static_cast<unsigned>(value >= 0 ? value : -value), 3);
    break;
  }
  case 'f':
  case 'p':
  case 't':
    hex(v.bytes[1], 2);
    hex(word(v), 3);
    break;
  case 'h':
  case 'l':
  case 'r':
    hex(v.bytes[1], 2);
    hex(v.bytes[2], 2);
    hex(v.bytes[3], 2);
    break;
  case 'j':
    hex(v.bytes[1], 1);
    hex(v.bytes[2], 1);
    hex(v.bytes[3], 2);
    break;
  default:
    return -2;
  }
  return finish();
}

extern "C" int uart_protocol_decode(const char *text, unsigned length,
                                    Uart_Msg_Type *message) {
  auto &v = *message;
  const unsigned op =
      static_cast<unsigned char>(text[static_cast<std::ptrdiff_t>(length) - 1]);
  auto hex = [&](int offset, int count) {
    return utils_Ascii2Int(text + offset, count);
  };
  auto tail = [&](int back, int count) {
    return hex(static_cast<int>(length) - back, count);
  };
  auto byte = [&](unsigned index, std::uint32_t value) {
    v.bytes[index] = static_cast<std::uint8_t>(value);
  };
  auto type = [&]() { byte(0, op); };
  switch (op) {
  case 'G':
  case 'g':
    if (length <= 4)
      return -3;
    type();
    word(v, tail(4, 3));
    byte(1, tail(5, 1));
    return 1;
  case 'H':
  case 'v':
    if (length <= 2)
      return -3;
    type();
    byte(1, tail(3, 2));
    return 1;
  case 'K':
    if (length <= 4)
      return -3;
    type();
    byte(1, tail(7, 2));
    word(v, tail(5, 4));
    return 1;
  case 'L':
    if (length <= 4)
      return -3;
    type();
    byte(3, tail(2, 1));
    byte(2, tail(4, 2));
    byte(1, tail(5, 1));
    return 1;
  case 'M':
    if (length <= 3)
      return -3;
    type();
    byte(1, tail(4, 2));
    byte(2, tail(2, 1));
    return 1;
  case 'N':
  case 'O':
    type();
    if (length <= 4)
      return -3;
    byte(1, tail(5, 2));
    byte(2, tail(3, 1));
    byte(3, tail(2, 1));
    return 1;
  case 'P':
    if (length <= 3) {
      return -3;
    }
    type();
    byte(1, tail(4, 1));
    byte(2, tail(3, 2));
    return 1;
  case 'R':
    if (length <= 3)
      return -3;
    type();
    byte(1, tail(4, 1));
    word(v, tail(3, 2));
    return 1;
  case 'S':
  case 's':
    if (length <= 3)
      return -4;
    type();
    byte(2, tail(3, 2));
    byte(1, tail(4, 1));
    byte(3, 0);
    return 1;
  case 'T':
  case 'U':
  case 'z': {
    if (length <= 7)
      return -3;
    const unsigned flags = tail(8, 1), x = tail(7, 3), y = tail(4, 3);
    byte(2, y);
    byte(3, ((x >> 8) & 3) * 4 + ((y >> 8) & 3) + flags * 16);
    type();
    byte(1, x);
    return 1;
  }
  case 'V':
    if (length <= 5)
      return -3;
    type();
    byte(3, tail(2, 1));
    byte(2, tail(4, 2));
    byte(1, tail(6, 2));
    return 1;
  case 'b':
    if (length <= 5)
      return -3;
    type();
    word(v, tail(5, 4));
    byte(1, tail(6, 1));
    return 1;
  case 'd':
  case 'm':
    if (length <= 4)
      return -3;
    type();
    byte(1, tail(5, 2));
    byte(2, tail(3, 2));
    return 1;
  case 'e': {
    if (length <= 6)
      return -3;
    type();
    byte(1, tail(7, 2));
    const unsigned sign = tail(5, 1) & 255, value = tail(4, 3) & 65535;
    word(v, value);
    if (sign != 1)
      word(v, 0 - value);
    return sign > 1 ? -3 : 1;
  }
  case 'f':
  case 'p':
  case 't':
    if (length <= 5)
      return -3;
    type();
    byte(1, tail(6, 2));
    word(v, tail(4, 3));
    return 1;
  case 'h':
  case 'r':
    if (length <= 6)
      return -3;
    type();
    byte(1, tail(7, 2));
    byte(2, tail(5, 2));
    byte(3, tail(3, 2));
    return 1;
  case 'l':
    if (length <= 6)
      return -3;
    type();
    byte(1, hex(0, 2));
    byte(2, hex(2, 2));
    byte(3, hex(4, 2));
    return 1;
  case 'j':
    if (length <= 4)
      return -3;
    type();
    byte(3, tail(3, 2));
    byte(1, tail(5, 1));
    byte(2, tail(4, 1));
    return 1;
  case 'x':
    if (length <= 3)
      return -3;
    type();
    byte(2, tail(3, 2));
    byte(1, tail(4, 1));
    return 1;
  default:
    return ((op >= '0' && op <= '9') || (op >= 'A' && op <= 'F')) ? 0 : -2;
  }
}
