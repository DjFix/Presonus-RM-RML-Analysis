#include "presonus/panel/simulate_comm.hpp"
#include "presonus/panel/uart_message_handler.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>
using Presonus::UARTMessageHandler;
extern "C" void uart_handler_virtual_destroy(Core::Portable::TypedObject *);
extern "C" void uart_handler_virtual_delete(Core::Portable::TypedObject *);
extern "C" void
handler_d1(UARTMessageHandler *) asm("_ZN8Presonus18UARTMessageHandlerD1Ev");
extern "C" void
handler_d0(UARTMessageHandler *) asm("_ZN8Presonus18UARTMessageHandlerD0Ev");
struct Context {
  void *object = nullptr;
  Uart_Msg_Type *message = nullptr;
  bool enabled = false, mutate = false;
  unsigned deletes = 0;
  std::vector<std::array<unsigned, 5>> events;
};
static Context *context;
void operator delete(void *p) noexcept {
  if (context && context->enabled && p == context->object)
    ++context->deletes;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
static void record(unsigned slot, unsigned a = 0, unsigned b = 0,
                   unsigned c = 0, unsigned alias = 0) {
  if (!context || !context->enabled)
    std::abort();
  context->events.push_back({slot, a, b, c, alias});
  if (context->mutate) {
    const unsigned char mask[4] = {0x10, 0x20, 0x40, 0x80};
    for (unsigned i = 0; i < 4; ++i)
      context->message->bytes[i] ^= mask[i];
  }
}
class Recorder final : public UARTMessageHandler {
public:
  void handleSwitch(int a, int b, bool c) override { record(4, a, b, c); }
  void handleFader(int a, int b) override { record(5, a, b); }
  void handleFaderStatus(int a, unsigned char b) override { record(6, a, b); }
  void handlePot(int a, int b) override { record(7, a, b); }
  void handleEncoder(int a, int b) override { record(8, a, b); }
  void handleTemperature(int a, int b) override { record(9, a, b); }
  void handleVersion(int a, Uart_Msg_Type &b) override {
    if (&b != context->message)
      std::abort();
    record(10, a, 0, 0, 1);
  }
  void handleError(int a, unsigned short b) override { record(11, a, b); }
  void handleTouchscreen(Touchscreen_Type &b) override {
    if (static_cast<void *>(&b) != context->message)
      std::abort();
    record(12, 0, 0, 0, 1);
  }
  void handleMovingFaderMcuStatus(unsigned char a, unsigned char b,
                                  unsigned char c) override {
    record(13, a, b, c);
  }
  void handleGlobalResponse(int a, Uart_Msg_Type &b) override {
    if (&b != context->message)
      std::abort();
    record(14, a, 0, 0, 1);
  }
  void handleCalibrateTouchscreenProgress(unsigned char a,
                                          unsigned short b) override {
    record(15, a, b);
  }
  void handleKeyValue(unsigned char a, unsigned short b) override {
    record(16, a, b);
  }
  void handleLineSense(int a, int b, int c) override { record(17, a, b, c); }
  void handleFaderSensitivity(unsigned short a) override { record(18, a); }
  void handleFaderSpeed(unsigned short a) override { record(19, a); }
};
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static int integer(unsigned n) {
  int v;
  std::memcpy(&v, &n, 4);
  return v;
}
static void append(std::vector<unsigned char> &out, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    out.push_back(static_cast<unsigned char>(n >> (8 * i)));
}
static void warmDiagnostic() {
  if (presonus::panel::uartDiagnosticBuffer())
    std::abort();
  UARTMessageHandler value;
  Uart_Msg_Type msg{{'R', 1, 0, 0}};
  value.processMsg(msg, 0);
  auto *p = presonus::panel::uartDiagnosticBuffer();
  if (!p)
    std::abort();
  for (unsigned i = 0; i < 128; ++i)
    if (p[i])
      std::abort();
  // Actual source dynamic/static initialization has occurred; fixture guard
  // ABI/callcounts are deliberately not fabricated/reset in native storage.
}
static std::vector<unsigned char>
run(const std::array<unsigned char, 152> &input) {
  unsigned op = word(input.data()), override = word(input.data() + 4),
           port = word(input.data() + 8);
  Context c;
  c.events.reserve(1);
  c.mutate = word(input.data() + 12) != 0;
  context = &c;
  Uart_Msg_Type msg;
  std::memcpy(msg.bytes.data(), input.data() + 20, 4);
  c.message = &msg;
  auto *object = override ? static_cast<UARTMessageHandler *>(new Recorder)
                          : new UARTMessageHandler;
  c.object = object;
  std::memcpy(presonus::panel::uartDiagnosticBuffer(), input.data() + 24, 128);
  c.enabled = true;
  unsigned result = 0;
  if (op == 0)
    object->processMsg(msg, integer(port));
  else if (op == 1) {
    auto *p = object->castTo(integer(port));
    if (p && p != object)
      std::abort();
    result = p == object;
  } else if (op == 2)
    uart_handler_virtual_destroy(object);
  else if (op == 3)
    uart_handler_virtual_delete(object);
  else if (op == 4)
    object->UARTMessageHandler::handleSwitch(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8),
        msg.bytes[1] & 1);
  else if (op == 5)
    object->UARTMessageHandler::handleFader(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 6)
    object->UARTMessageHandler::handleFaderStatus(msg.bytes[1], msg.bytes[2]);
  else if (op == 7)
    object->UARTMessageHandler::handlePot(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 8)
    object->UARTMessageHandler::handleEncoder(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 9)
    object->UARTMessageHandler::handleTemperature(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 10)
    object->UARTMessageHandler::handleVersion(integer(port), msg);
  else if (op == 11)
    object->UARTMessageHandler::handleError(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 12)
    object->UARTMessageHandler::handleTouchscreen(
        reinterpret_cast<Touchscreen_Type &>(msg));
  else if (op == 13)
    object->UARTMessageHandler::handleMovingFaderMcuStatus(
        msg.bytes[1], msg.bytes[2], msg.bytes[3]);
  else if (op == 14)
    object->UARTMessageHandler::handleGlobalResponse(integer(port), msg);
  else if (op == 15)
    object->UARTMessageHandler::handleCalibrateTouchscreenProgress(
        msg.bytes[1], msg.bytes[2]);
  else if (op == 16)
    object->UARTMessageHandler::handleKeyValue(msg.bytes[1], msg.bytes[2]);
  else if (op == 17)
    object->UARTMessageHandler::handleLineSense(
        integer(port), msg.bytes[2] | (unsigned(msg.bytes[3]) << 8),
        msg.bytes[1] & 1);
  else if (op == 18)
    object->UARTMessageHandler::handleFaderSensitivity(
        msg.bytes[2] | (unsigned(msg.bytes[3]) << 8));
  else if (op == 19)
    object->UARTMessageHandler::handleFaderSpeed(msg.bytes[2] |
                                                 (unsigned(msg.bytes[3]) << 8));
  else
    std::abort();
  if (c.events.size() > 1)
    std::abort();
  c.enabled =
      false; // End observation before output allocations can reuse D0 storage.
  std::vector<unsigned char> out;
  append(out, result);
  append(out, c.deletes);
  append(out, c.events.size());
  auto event = c.events.empty() ? std::array<unsigned, 5>{} : c.events[0];
  for (unsigned n : event)
    append(out, n);
  out.insert(out.end(), msg.bytes.begin(), msg.bytes.end());
  const auto *buffer = presonus::panel::uartDiagnosticBuffer();
  out.insert(out.end(), buffer, buffer + 128);
  c.enabled = false;
  if (op != 2 && op != 3)
    delete object;
  else if (op == 2)
    ::operator delete(object);
  context = nullptr;
  return out;
}
static void slotsAndComposition() {
  UARTMessageHandler base;
  void **slots = nullptr;
  std::memcpy(&slots, &base, sizeof(slots));
  if (slots[1] != reinterpret_cast<void *>(handler_d1) ||
      slots[2] != reinterpret_cast<void *>(handler_d0))
    std::abort();
  if (base.castTo(0x75617274) != &base || base.castTo(0))
    std::abort();
  Presonus::Panel::SimulateComm left(false), right(true);
  if (left.open("offline") != 1)
    std::abort();
  Uart_Msg_Type send{{'G', 3, 0x23, 1}}, receive{{0, 0, 0, 0}};
  if (left.writeMsg(send) != 1 || right.readMsg(receive) != 1 ||
      receive.bytes != send.bytes)
    std::abort();
  Context c;
  c.events.reserve(1);
  c.enabled = true;
  c.message = &receive;
  context = &c;
  Recorder parser;
  c.object = &parser;
  parser.processMsg(receive, -7);
  if (c.events != std::vector<std::array<unsigned, 5>>{
                      {14, static_cast<unsigned>(-7), 0, 0, 1}})
    std::abort();
  c.enabled = false;
  context = nullptr;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  warmDiagnostic();
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), 12);
  if (!f || std::memcmp(header.data(), "UHNDv001", 8))
    return 3;
  unsigned count = word(header.data() + 8);
  for (unsigned i = 0; i < count; ++i) {
    std::array<unsigned char, 152> input;
    std::array<unsigned char, 164> expected;
    f.read(reinterpret_cast<char *>(input.data()), 152);
    f.read(reinterpret_cast<char *>(expected.data()), 164);
    if (!f)
      return 4;
    auto actual = run(input);
    if (actual.size() != expected.size())
      return 5;
    for (unsigned j = 0; j < expected.size(); ++j)
      if (actual[j] != expected[j]) {
        std::fprintf(
            stderr,
            "Mismatch case%u op%u override%u offset%u original%u native%u\n", i,
            word(input.data()), word(input.data() + 4), j, expected[j],
            actual[j]);
        return 6;
      }
  }
  slotsAndComposition();
  std::printf("PASS %u original UARTMessageHandler fixtures plus actual "
              "CCL/static/transport composition\n",
              count);
}
