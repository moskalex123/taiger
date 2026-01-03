#!/usr/bin/env python3
"""
Script to display test results in a readable format
"""

import json
import sys

def main():
    try:
        with open('messages.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=" * 60)
        print("COMPREHENSIVE MODEL TESTING RESULTS")
        print("=" * 60)
        print(f"Test Run Timestamp: {data['test_run_timestamp']}")
        print(f"Total Texts Processed: {data['total_texts_processed']}")
        print(f"Total Responses Collected: {data['total_responses']}")
        print()
        
        # Calculate successful vs error responses
        successful = len([r for r in data['responses'] if r['model_id'] != -1])
        errors = len([r for r in data['responses'] if r['model_id'] == -1])
        print(f"Successful Responses: {successful}")
        print(f"Error Responses: {errors}")
        print()
        
        # Show models that responded
        model_names = sorted(set([r['model_name'] for r in data['responses'] if r['model_id'] != -1]))
        print(f"Models That Responded ({len(model_names)}):")
        for name in model_names:
            count = len([r for r in data['responses'] if r['model_name'] == name])
            print(f"  - {name} ({count} responses)")
        print()
        
        # Show responses per text
        print("Responses per Test Text:")
        test_texts = [
            "Завтра в нашем магазине скидка 20% на все.",
            "Ребята, какой ноутбук посоветуете для учебы? Бюджет до 50к.",
            "В общем, такая ситуация, пришел я сегодня на работу...",
            "Чтобы настроить программу, вам нужно сначала открыть ее...",
            "Митап по маркетингу в субботу, 15 числа...",
            "Мы делаем сайты под ключ. Качественно и недорого...",
            "ВАЩЕ КЛАССНАЯ АКЦИЯ У НАС ВСЕ ТОВАРЫ СО СКИДКОЙ 50 ПРОЦЕНТОВ...",
            "Настоящим уведомляем о проведении технических работ...",
            "Что вы думаете о новой функции?",
            "Сегодня видел, как ворона каталась на скейте..."
        ]
        
        for i in range(10):
            count = len([r for r in data['responses'] if r['test_text_index'] == i])
            text_preview = test_texts[i][:50] + "..." if len(test_texts[i]) > 50 else test_texts[i]
            print(f"  Text {i+1}: {count} responses - \"{text_preview}\"")
        print()
        
        # Show some example responses
        print("Sample Responses:")
        for i, response in enumerate(data['responses'][:5]):
            print(f"  {i+1}. Model {response['model_name']} (ID: {response['model_id']})")
            print(f"     Time: {response['processing_time']}s")
            print(f"     Response: {response['response_text'][:100]}...")
            print()
            
    except FileNotFoundError:
        print("Error: messages.json file not found. Please run the complete test first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()