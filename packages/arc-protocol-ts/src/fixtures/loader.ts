/**
 * Cross-language fixture loader for TypeScript tests.
 * 
 * Loads JSON fixtures from protocol/fixtures/ and validates them against
 * TypeScript types to ensure Python ↔ TypeScript schema consistency.
 */

import * as fs from 'fs';
import * as path from 'path';

// Path to fixtures directory relative to this file
const FIXTURES_DIR = path.join(__dirname, '../../../../protocol/fixtures');

/**
 * Load a JSON fixture by category and name.
 * 
 * @param category - Fixture category (e.g., 'arc-envelope', 'run-event')
 * @param name - Fixture name without .json extension (e.g., 'success', 'run-completed')
 * @returns Parsed JSON object
 * @throws Error if fixture file doesn't exist or is invalid JSON
 * 
 * @example
 * const envelope = loadFixture('arc-envelope', 'success');
 * expect(envelope.ok).toBe(true);
 */
export function loadFixture(category: string, name: string): unknown {
  const fixturePath = path.join(FIXTURES_DIR, category, `${name}.json`);
  
  if (!fs.existsSync(fixturePath)) {
    throw new Error(
      `Fixture not found: ${category}/${name}.json\n` +
      `Expected at: ${fixturePath}`
    );
  }
  
  const content = fs.readFileSync(fixturePath, 'utf-8');
  return JSON.parse(content);
}

/**
 * Load a fixture and validate it matches a TypeScript type.
 * 
 * @param category - Fixture category
 * @param name - Fixture name without .json extension
 * @param validator - Function that validates and narrows the type
 * @returns Validated and typed object
 * 
 * @example
 * const envelope = loadAndValidate('arc-envelope', 'success', validateEnvelope);
 * expect(envelope.ok).toBe(true);
 */
export function loadAndValidate<T>(
  category: string,
  name: string,
  validator: (data: unknown) => T
): T {
  const data = loadFixture(category, name);
  return validator(data);
}

/**
 * Load fixture, validate, serialize back to JSON, and compare.
 * 
 * Tests that:
 * 1. Fixture is valid according to TypeScript type
 * 2. Type can serialize back to JSON
 * 3. Serialized JSON matches original fixture (schema stability)
 * 
 * @param category - Fixture category
 * @param name - Fixture name without .json extension
 * @param validator - Function that validates the type
 * @returns Tuple of [original, serialized, instance]
 */
export function validateRoundTrip<T>(
  category: string,
  name: string,
  validator: (data: unknown) => T
): [unknown, unknown, T] {
  const original = loadFixture(category, name);
  const instance = validator(original);
  const serialized = JSON.parse(JSON.stringify(instance));
  return [original, serialized, instance];
}

/**
 * List all fixture names in a category.
 * 
 * @param category - Fixture category
 * @returns Array of fixture names (without .json extension)
 * 
 * @example
 * const fixtures = listFixtures('arc-envelope');
 * expect(fixtures).toContain('success');
 */
export function listFixtures(category: string): string[] {
  const categoryDir = path.join(FIXTURES_DIR, category);
  
  if (!fs.existsSync(categoryDir)) {
    return [];
  }
  
  return fs.readdirSync(categoryDir)
    .filter(f => f.endsWith('.json'))
    .map(f => f.replace('.json', ''));
}

/**
 * List all fixture categories.
 * 
 * @returns Array of category names
 * 
 * @example
 * const categories = listCategories();
 * expect(categories).toContain('arc-envelope');
 */
export function listCategories(): string[] {
  if (!fs.existsSync(FIXTURES_DIR)) {
    return [];
  }
  
  return fs.readdirSync(FIXTURES_DIR)
    .filter(f => fs.statSync(path.join(FIXTURES_DIR, f)).isDirectory());
}
