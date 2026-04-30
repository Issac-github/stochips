import * as $protobuf from 'protobufjs'

import Long = require('long')
/** Namespace data. */
export namespace data {
  /** Properties of a Strategy. */
  interface IStrategy {
    /** Strategy id */
    id?: string | null

    /** Strategy name */
    name?: string | null

    /** Strategy description */
    description?: string | null
  }

  /** Represents a Strategy. */
  class Strategy implements IStrategy {
    /**
     * Constructs a new Strategy.
     * @param [properties] Properties to set
     */
    constructor(properties?: data.IStrategy)

    /** Strategy id. */
    public id: string

    /** Strategy name. */
    public name: string

    /** Strategy description. */
    public description: string

    /**
     * Creates a new Strategy instance using the specified properties.
     * @param [properties] Properties to set
     * @returns Strategy instance
     */
    public static create(properties?: data.IStrategy): data.Strategy

    /**
     * Encodes the specified Strategy message. Does not implicitly {@link data.Strategy.verify|verify} messages.
     * @param message Strategy message or plain object to encode
     * @param [writer] Writer to encode to
     * @returns Writer
     */
    public static encode(
      message: data.IStrategy,
      writer?: $protobuf.Writer
    ): $protobuf.Writer

    /**
     * Encodes the specified Strategy message, length delimited. Does not implicitly {@link data.Strategy.verify|verify} messages.
     * @param message Strategy message or plain object to encode
     * @param [writer] Writer to encode to
     * @returns Writer
     */
    public static encodeDelimited(
      message: data.IStrategy,
      writer?: $protobuf.Writer
    ): $protobuf.Writer

    /**
     * Decodes a Strategy message from the specified reader or buffer.
     * @param reader Reader or buffer to decode from
     * @param [length] Message length if known beforehand
     * @returns Strategy
     * @throws {Error} If the payload is not a reader or valid buffer
     * @throws {$protobuf.util.ProtocolError} If required fields are missing
     */
    public static decode(
      reader: $protobuf.Reader | Uint8Array,
      length?: number
    ): data.Strategy

    /**
     * Decodes a Strategy message from the specified reader or buffer, length delimited.
     * @param reader Reader or buffer to decode from
     * @returns Strategy
     * @throws {Error} If the payload is not a reader or valid buffer
     * @throws {$protobuf.util.ProtocolError} If required fields are missing
     */
    public static decodeDelimited(
      reader: $protobuf.Reader | Uint8Array
    ): data.Strategy

    /**
     * Verifies a Strategy message.
     * @param message Plain object to verify
     * @returns `null` if valid, otherwise the reason why it is not
     */
    public static verify(message: { [k: string]: any }): string | null

    /**
     * Creates a Strategy message from a plain object. Also converts values to their respective internal types.
     * @param object Plain object
     * @returns Strategy
     */
    public static fromObject(object: { [k: string]: any }): data.Strategy

    /**
     * Creates a plain object from a Strategy message. Also converts values to other types if specified.
     * @param message Strategy
     * @param [options] Conversion options
     * @returns Plain object
     */
    public static toObject(
      message: data.Strategy,
      options?: $protobuf.IConversionOptions
    ): { [k: string]: any }

    /**
     * Converts this Strategy to JSON.
     * @returns JSON object
     */
    public toJSON(): { [k: string]: any }

    /**
     * Gets the default type url for Strategy
     * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
     * @returns The default type url
     */
    public static getTypeUrl(typeUrlPrefix?: string): string
  }
}
