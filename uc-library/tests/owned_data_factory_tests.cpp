#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/owned_data_factory_codec.hpp"
#include <algorithm>
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>
using namespace presonus::uc;
using namespace Presonus::UC;
namespace {
void check(bool value) {
  if (!value)
    throw std::runtime_error("owned factory provider check");
}
std::size_t cases = 0;
void word(std::vector<unsigned char> &bytes, std::uint32_t value,
          bool big = false) {
  for (unsigned i = 0; i != 4; ++i)
    bytes.push_back(
        static_cast<unsigned char>(value >> (8 * (big ? 3 - i : i))));
}
template <class Codec> void exercise() {
  using Value = typename Codec::value_type;
  Codec codec;
  CclFactoryRegistry registry(32);
  codec.registerIn(registry.registry());
  EventFactory factory(registry.registry());
  check(factory.createType(-1) == nullptr);
  for (unsigned length : {0u, 1u, 3u, 17u, 255u}) {
    std::vector<unsigned char> input(length);
    for (unsigned n = 0; n < length; ++n)
      input[n] = static_cast<unsigned char>(n * 73 + 17);
    Value value{};
    value.header = {unsigned(Codec::type), 0xdeadbeef, 0x12345, 0xabcde};
    value.data = input.empty() ? nullptr : input.data();
    value.sizeBits = length;
    if constexpr (Codec::payload_words > 0)
      value.word24 = 0x81234567;
    if constexpr (Codec::payload_words > 1) {
      value.word28 = 0xdeadbeef;
      value.word32 = 0x7f812345;
    }
    const Value *resolved = nullptr;
    check(!codec.resolve(value.header, resolved) && resolved == nullptr);
    check(factory.create(value.header) == nullptr);
    codec.bind(value);
    check(codec.resolve(value.header, resolved) && resolved == &value);
    codec.bind(value); // Replacement retains one live exact-identity binding.
    std::unique_ptr<EventItem> cloned(factory.create(value.header));
    auto *typed = dynamic_cast<OwnedCodecItem<Value> *>(cloned.get());
    check(typed && typed->value.header.reserved04 == 0xdeadbeef &&
          typed->value.header.routeA == 0x12345 &&
          typed->value.sizeBits == length);
    if (length) {
      check(typed->value.data != input.data());
      check(std::memcmp(typed->value.data, input.data(), length) == 0);
      input[0] ^= 0xff;
      check(static_cast<const unsigned char *>(typed->value.data)[0] !=
            input[0]);
      input[0] ^= 0xff;
    }
    std::vector<unsigned char> expected = {
        static_cast<unsigned char>(Codec::type >> 8),
        static_cast<unsigned char>(Codec::type),
        0x45,
        0x23,
        0xde,
        0xbc};
    if constexpr (Codec::payload_words > 0)
      word(expected, value.word24, true);
    if constexpr (Codec::payload_words > 1) {
      word(expected, value.word28);
      word(expected, value.word32);
    }
    word(expected, length);
    expected.insert(expected.end(), input.begin(), input.end());
    std::array<unsigned char, 512> encoded{};
    check(factory.write(reinterpret_cast<char *>(encoded.data()),
                        encoded.size(), value.header) == int(expected.size()));
    check(std::equal(expected.begin(), expected.end(), encoded.begin()));
    for (unsigned capacity = 0; capacity <= expected.size() + 1; ++capacity) {
      std::array<unsigned char, 512> guarded;
      guarded.fill(0xa5);
      BufferWriter writer(guarded.data() + 8, capacity);
      const auto &callbacks = codec.codec();
      bool success = callbacks.write(callbacks.context, writer, value.header);
      check(success == (capacity >= expected.size()));
      check(writer.position() >= 0 && writer.position() <= int(capacity));
      check(std::all_of(guarded.begin(), guarded.begin() + 8,
                        [](auto b) { return b == 0xa5; }));
      check(std::all_of(guarded.begin() + 8 + capacity, guarded.end(),
                        [](auto b) { return b == 0xa5; }));
      BufferReader reader(encoded.data(), capacity);
      std::unique_ptr<EventItem> decoded(factory.read(reader));
      check(bool(decoded) == (capacity >= expected.size()));
      if (decoded) {
        auto *data = dynamic_cast<OwnedCodecItem<Value> *>(decoded.get());
        check(data && data->value.header.type == unsigned(Codec::type) &&
              data->value.header.routeA == 0x2345 &&
              data->value.header.routeB == 0xbcde &&
              data->value.sizeBits == length);
        check(reader.position() == int(expected.size()));
        if (length)
          check(std::memcmp(data->value.data, input.data(), length) == 0);
      }
      ++cases;
    }
    auto created = std::unique_ptr<EventItem>(factory.createType(Codec::type));
    auto *empty = dynamic_cast<OwnedCodecItem<Value> *>(created.get());
    check(empty && empty->value.header.type == unsigned(Codec::type) &&
          empty->value.header.reserved04 == 24 + Codec::payload_words * 4 &&
          empty->value.sizeBits == 0);
    codec.unbind(value);
    check(!codec.resolve(value.header, resolved) && resolved == nullptr);
    check(factory.create(value.header) == nullptr);
  }
}
} // namespace
int main() {
  exercise<BinaryFactoryCodec>();
  exercise<MessageChunkFactoryCodec>();
  exercise<EncodedDataFactoryCodec<23117>>();
  exercise<EncodedDataFactoryCodec<19021>>();
  exercise<EncodedDataFactoryCodec<21826>>();
  exercise<EncodedDataFactoryCodec<23106>>();
  exercise<LoopbackQueryDataFactoryCodec>();
  exercise<LoopbackReplyDataFactoryCodec>();
  exercise<MidiLongSysexDataFactoryCodec>();
  std::cout << "nine actual CCL owned-data providers PASS; bounded cut cases="
            << cases << '\n';
}
