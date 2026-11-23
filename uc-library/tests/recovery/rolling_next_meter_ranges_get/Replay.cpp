#include "presonus/MeterScaleControl.hpp"
#include <iostream>
#include <string>
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  using Ranges = Presonus::MeterScaleControl::Ranges;
  Ranges ranges{Ranges::SourcePortTag{}};
  int values[] = {50, 60};
  std::string names[] = {"", "A", "A", "a", std::string(127, 'x'), "tail"};
  int n = std::stoi(argv[1]);
  for (int i = 0; i < n; ++i)
    ranges.addRange(names[i].c_str(), i, values);
  auto key = std::string(argv[2]);
  auto *found = ranges.getRange(key == "@NULL" ? nullptr : key.c_str());
  int result = -1;
  for (int i = 0; i < n; ++i) {
    const auto *record = ranges.at(i);
    if (record->values != values || record->count != i ||
        record->name.str() != names[i])
      return 3;
    if (record == found)
      result = i;
  }
  if (ranges.count() != n)
    return 4;
  std::cout << result << '\n';
}
