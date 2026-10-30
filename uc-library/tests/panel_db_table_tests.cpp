#include "presonus/surface_panel/DbTable.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <new>
#include <sstream>
#include <string>
#include <type_traits>

using Presonus::Panel::DbTable;
static_assert(sizeof(DbTable) == 140);
static_assert(std::is_trivially_copyable_v<DbTable>);
static float floatBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    char operation;
    unsigned role;
    std::uint32_t a, b, expectedReturn;
    std::array<std::uint32_t, 35> before{}, expected{}, actual{};
    std::array<float, 16> decibels{};
    if (!(row >> operation >> role >> a >> b >> expectedReturn))
      return 3;
    for (auto &value : before)
      row >> value;
    for (auto &value : decibels) {
      std::uint32_t bits;
      row >> bits;
      value = floatBits(bits);
    }
    for (auto &value : expected)
      row >> value;
    if (!row)
      return 4;
    alignas(DbTable) unsigned char storage[sizeof(DbTable)];
    std::memcpy(storage, before.data(), sizeof(storage));
    const auto count = static_cast<std::int32_t>(a);
    const float *data = count > 0 ? decibels.data() : nullptr;
    auto *table = operation == 'A' || operation == 'B'
                      ? new (storage) DbTable(data, count)
                      : new (storage) DbTable(nullptr, 0);
    std::uint32_t result = 0;
    if (operation != 'A' && operation != 'B') {
      std::memcpy(table, before.data(), sizeof(DbTable));
      switch (operation) {
      case 'S':
        table->setup(data, count);
        break;
      case 'R':
        table->setDbRange(floatBits(a), floatBits(b));
        break;
      case 'C':
        result = static_cast<std::uint32_t>(table->getCount());
        break;
      case 'G':
        result =
            static_cast<std::uint32_t>(table->getStepFromGain(floatBits(a)));
        break;
      case 'N':
        result = static_cast<std::uint32_t>(
            table->getStepFromNormalizedDB(floatBits(a)));
        break;
      default:
        return 5;
      }
    }
    std::memcpy(actual.data(), table, sizeof(DbTable));
    table->~DbTable();
    if (actual != expected || result != expectedReturn) {
      std::fprintf(stderr, "Mismatch case %u op %c role %u return %u/%u\n",
                   cases, operation, role, result, expectedReturn);
      for (unsigned i = 0; i < actual.size(); ++i)
        if (actual[i] != expected[i])
          std::fprintf(stderr, "word %u %08x/%08x\n", i, actual[i],
                       expected[i]);
      return 1;
    }
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 6;
  std::printf("PASS: %u original ARM DbTable differential cases\n", cases);
}
