/*eslint-disable block-scoped-var, id-length, no-control-regex, no-magic-numbers, no-prototype-builtins, no-redeclare, no-shadow, no-var, sort-vars*/
import * as $protobuf from 'protobufjs/light'

const $root = (
  $protobuf.roots['default'] ||
  ($protobuf.roots['default'] = new $protobuf.Root())
).addJSON({
  data: {
    nested: {
      Strategy: {
        fields: {
          id: {
            type: 'string',
            id: 1
          },
          name: {
            type: 'string',
            id: 2
          },
          description: {
            type: 'string',
            id: 3
          }
        }
      }
    }
  }
})

export { $root as default }
