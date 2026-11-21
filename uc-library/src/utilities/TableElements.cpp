#include "presonus/utilities/table_elements.hpp"

int countTableElements(const int *table) {
  int count = 0;
  while (table[count] != -1)
    ++count;
  return count;
}
