#include "presonus/application/ResourceLibrary.hpp"
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace presonus::application {
struct ResourceAccess {
  static void set(Presonus::FirmwareBundle &b, const unsigned char *input,
                  int size, bool compressed) {
    b.name_ = "fixture";
    b.version_ = 0;
    b.image_ = input;
    b.image_size_ = size;
    b.compressed_ = compressed;
    b.stream_ = {}; // Explicit fixture state, never an original ctor claim.
  }
  static z_stream &stream(Presonus::FirmwareBundle &b) { return b.stream_; }
  static const unsigned char *input(Presonus::FirmwareBundle &b) {
    return b.image_;
  }
  static int size(Presonus::FirmwareBundle &b) { return b.image_size_; }
};
} // namespace presonus::application
namespace {
using Bundle = Presonus::FirmwareBundle;
using Access = presonus::application::ResourceAccess;
void require(bool value) {
  if (!value)
    std::abort();
}
std::string hex(const std::string &s) {
  constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (unsigned char byte : s) {
    out += digits[byte >> 4];
    out += digits[byte & 15];
  }
  return out.empty() ? "-" : out;
}
std::string unhex(const std::string &s) {
  if (s == "-")
    return {};
  require(s.size() % 2 == 0);
  std::string out;
  for (std::size_t i = 0; i < s.size(); i += 2)
    out += static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16));
  return out;
}
struct State {
  z_stream snapshot{};
  void *identity = nullptr;
  bool alive = true;
};
struct Context {
  std::vector<unsigned char> input;
  std::vector<unsigned char> output;
  std::unique_ptr<Bundle> bundle = std::make_unique<Bundle>();
  std::vector<State> states;
  std::vector<std::string> trace;
  int fault = 0;
};
std::unique_ptr<Context> context;
void capture(z_streamp stream, bool /*fresh*/) {
  if (!stream->state)
    return;
  State *state = nullptr;
  for (auto &entry : context->states)
    if (entry.alive && entry.identity == stream->state)
      state = &entry;
  if (!state) {
    context->states.push_back(State{});
    state = &context->states.back();
    state->identity = stream->state;
  }
  std::memcpy(&state->snapshot, stream, sizeof(z_stream));
}
std::string status(z_streamp stream) {
  return std::to_string(stream->avail_in) + "," +
         std::to_string(stream->avail_out) + "," +
         std::to_string(stream->total_in) + "," +
         std::to_string(stream->total_out) + "," + (stream->state ? "1" : "0");
}
unsigned live() {
  unsigned result = 0;
  for (const auto &entry : context->states)
    result += entry.alive;
  return result;
}
unsigned char *prepareOutput(int size, bool nullOutput) {
  require(nullOutput || (size >= 0 && size <= 16384));
  const unsigned count = nullOutput ? 0 : static_cast<unsigned>(size);
  context->output.assign(count + 32, 0xa5);
  return nullOutput ? nullptr : context->output.data() + 16;
}
void printRead(int result) {
  const auto &bytes = context->output;
  require(std::all_of(bytes.begin(), bytes.begin() + 16,
                      [](auto x) { return x == 0xa5; }));
  require(std::all_of(bytes.end() - 16, bytes.end(),
                      [](auto x) { return x == 0xa5; }));
  std::cout << result << ' ' << Access::stream(*context->bundle).avail_out
            << ' ' << hex(std::string(bytes.begin(), bytes.end())) << '\n';
}
} // namespace
extern "C" int __real_inflateInit2_(z_streamp, int, const char *, int);
extern "C" int __real_inflate(z_streamp, int);
extern "C" int __real_inflateEnd(z_streamp);
extern "C" int __wrap_inflateInit2_(z_streamp stream, int bits,
                                    const char *version, int size) {
  require(context && bits == 31 && size == sizeof(z_stream));
  require(std::string(version) == ZLIB_VERSION);
  const int fault = context->fault;
  context->fault = 0;
  const int result =
      fault ? fault : __real_inflateInit2_(stream, bits, version, size);
  if (result == Z_OK)
    capture(stream, true);
  context->trace.push_back("init " + std::to_string(bits) + " " + version +
                           " " + std::to_string(size) + " " +
                           std::to_string(result) + " " +
                           std::to_string(fault != 0) + " " + status(stream));
  return result;
}
extern "C" int __wrap_inflate(z_streamp stream, int flush) {
  require(context && flush == Z_NO_FLUSH);
  const int result = __real_inflate(stream, flush);
  capture(stream, false);
  context->trace.push_back("inflate " + std::to_string(flush) + " " +
                           std::to_string(result) + " " + status(stream));
  return result;
}
extern "C" int __wrap_inflateEnd(z_streamp stream) {
  require(static_cast<bool>(context));
  void *identity = stream->state;
  const int result = __real_inflateEnd(stream);
  if (result == Z_OK)
    for (auto &entry : context->states)
      if (entry.alive && entry.identity == identity)
        entry.alive = false;
  context->trace.push_back("end " + std::to_string(result) + " " +
                           status(stream));
  return result;
}
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op, arg;
    in >> op;
    if (op == "info") {
      std::cout << ZLIB_VERSION << ' ' << zlibVersion() << ' '
                << sizeof(z_stream) << ' ' << sizeof(uInt) << '\n';
    } else if (op == "begin") {
      require(!context);
      int size, compressed, nullInput, fault;
      in >> arg >> size >> compressed >> nullInput >> fault;
      require((compressed == 0 || compressed == 1) &&
              (nullInput == 0 || nullInput == 1));
      const auto bytes = unhex(arg);
      require(bytes.size() <= 16384);
      require(nullInput ||
              (size >= 0 && static_cast<std::size_t>(size) <= bytes.size()));
      context = std::make_unique<Context>();
      context->fault = fault;
      context->input.assign(bytes.begin(), bytes.end());
      if (context->input.empty())
        context->input.push_back(0);
      Access::set(*context->bundle, nullInput ? nullptr : context->input.data(),
                  size, compressed != 0);
      std::cout << "OK\n";
    } else if (op == "native_open" || op == "native_close") {
      require(static_cast<bool>(context));
      std::cout << (op == "native_open" ? context->bundle->openBinImage()
                                        : context->bundle->closeBinImage())
                << '\n';
    } else if (op == "legacy_init") {
      int oldSize, bits;
      in >> arg >> oldSize >> bits;
      require(unhex(arg) == "1.2.11" && oldSize == 56 && bits == 31);
      auto &stream = Access::stream(*context->bundle);
      stream.next_in = const_cast<Bytef *>(Access::input(*context->bundle));
      stream.avail_in = static_cast<uInt>(Access::size(*context->bundle));
      stream.zalloc = Z_NULL;
      stream.zfree = Z_NULL;
      stream.opaque = Z_NULL;
      // Explicit ARM32-to-native zlib ABI adaptation, preserved in protocol.
      std::cout << inflateInit2_(&stream, bits, ZLIB_VERSION, sizeof(z_stream))
                << '\n';
    } else if (op == "legacy_end") {
      std::cout << inflateEnd(&Access::stream(*context->bundle)) << '\n';
    } else if (op == "legacy_inflate" || op == "native_read") {
      int size, nullOutput;
      in >> size >> nullOutput;
      require(context && (nullOutput == 0 || nullOutput == 1));
      auto *output = prepareOutput(size, nullOutput != 0);
      int result;
      if (op == "native_read")
        result = context->bundle->readBinImageBlock(output, size);
      else {
        auto &stream = Access::stream(*context->bundle);
        stream.next_out = output;
        stream.avail_out = static_cast<uInt>(size);
        result = inflate(&stream, Z_NO_FLUSH);
      }
      printRead(result);
    } else if (op == "trace") {
      require(static_cast<bool>(context));
      std::cout << context->trace.size();
      for (const auto &entry : context->trace)
        std::cout << ' ' << hex(entry);
      std::cout << ' ' << live() << '\n';
    } else if (op == "cleanup") {
      require(static_cast<bool>(context));
      auto &stream = Access::stream(*context->bundle);
      const unsigned before = live();
      // Fixture-only cleanup after trace collection; it is not product
      // behavior.
      for (auto &entry : context->states)
        if (entry.alive) {
          std::memcpy(&stream, &entry.snapshot, sizeof(z_stream));
          require(__real_inflateEnd(&stream) == Z_OK);
          entry.alive = false;
        }
      context.reset();
      std::cout << before << '\n';
    } else if (op == "quit") {
      require(!context);
      std::cout << "OK\n" << std::flush;
      return 0;
    } else
      return 2;
    std::cout << std::flush;
  }
  return 3;
}
