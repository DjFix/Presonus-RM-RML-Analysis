#include "presonus/utilities/table_elements.hpp"
#include <algorithm>
#include <iostream>
#include <vector>

int main() {
  std::vector<int> table;
  int value = 0;
  while (std::cin >> value)
    table.push_back(value);
  if (std::find(table.begin(), table.end(), -1) == table.end())
    return 2;
  std::cout << countTableElements(table.data()) << '\n';
}
