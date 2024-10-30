import asyncio
from asyncio import sleep as async_sleep, Lock, Queue, Semaphore

class Pizza:
    TYPES = {
        'Margherita': {'make': 2, 'bake': 4, 'pack': 1},
        'Pepperoni': {'make': 3, 'bake': 5, 'pack': 2},
        'Veggie': {'make': 1, 'bake': 3, 'pack': 1},
    }
    PRIORITIES = {'Normal': 1, 'Urgent': 0}

    def __init__(self, pizza_number, pizza_type, priority='Normal'):
        self.pizza = pizza_number
        self.status = 'in_fridge'
        self.type = pizza_type
        self.priority = priority

    STATUSES = (
        'in_fridge', 'to_make', 'made', 'in_oven', 'baked',
        'to_pack', 'to_deliver', 'delivered'
    )


class PizzaSpecialist:
    def __init__(self, specialist_type, number):
        self.specialist_type = specialist_type
        self.lock = Lock()
        self.active_pizza = None
        self.number = number

    async def make_busy(self, seconds, pizza):
        await self.lock.acquire()
        self.active_pizza = pizza
        await async_sleep(seconds)
        self.lock.release()

    async def get_ingredients_from_fridge(self, pizza):
        await self.make_busy(1, pizza)
        pizza.status = 'to_make'
        await make_queue.put(pizza)

    async def make_pizza(self, pizza):
        await self.make_busy(Pizza.TYPES[pizza.type]['make'], pizza)
        pizza.status = 'made'
        if pizza.priority == 'Urgent':
            await urgent_oven_queue.put(pizza)
        else:
            await normal_oven_queue.put(pizza)

    async def put_into_oven(self, pizza, ovens_semaphore):
        await ovens_semaphore.acquire()
        await self.make_busy(Pizza.TYPES[pizza.type]['bake'], pizza)
        pizza.status = 'in_oven'
        await oven_queue.put(pizza)

    async def take_out_of_oven(self, pizza, ovens_semaphore):
        await self.make_busy(1, pizza)
        ovens_semaphore.release()
        pizza.status = 'to_pack'
        await pack_queue.put(pizza)

    async def pack_pizza(self, pizza):
        await self.make_busy(Pizza.TYPES[pizza.type]['pack'], pizza)
        pizza.status = 'to_deliver'
        await deliver_queue.put(pizza)

    async def deliver_pizza(self, pizza):
        await self.make_busy(1, pizza)
        pizza.status = 'delivered'

    async def do_the_job(self, ovens_semaphore):
        while True:
            if not deliver_queue.empty():
                pizza = await deliver_queue.get()
                if pizza.type == self.specialist_type:
                    await self.deliver_pizza(pizza)
                else:
                    await deliver_queue.put(pizza)
                    await async_sleep(0.1)

            elif not pack_queue.empty():
                pizza = await pack_queue.get()
                if pizza.type == self.specialist_type:
                    await self.pack_pizza(pizza)
                else:
                    await pack_queue.put(pizza)
                    await async_sleep(0.1)

            elif not take_out_of_oven_queue.empty():
                pizza = await take_out_of_oven_queue.get()
                if pizza.type == self.specialist_type:
                    await self.take_out_of_oven(pizza, ovens_semaphore)
                else:
                    await take_out_of_oven_queue.put(pizza)
                    await async_sleep(0.1)

            elif not urgent_oven_queue.empty() and not ovens_semaphore.locked():
                pizza = await urgent_oven_queue.get()
                if pizza.type == self.specialist_type:
                    await self.put_into_oven(pizza, ovens_semaphore)
                else:
                    await urgent_oven_queue.put(pizza)
                    await async_sleep(0.1)

            elif not normal_oven_queue.empty() and not ovens_semaphore.locked():
                pizza = await normal_oven_queue.get()
                if pizza.type == self.specialist_type:
                    await self.put_into_oven(pizza, ovens_semaphore)
                else:
                    await normal_oven_queue.put(pizza)
                    await async_sleep(0.1)

            elif not make_queue.empty():
                pizza = await make_queue.get()
                if pizza.type == self.specialist_type:
                    await self.make_pizza(pizza)
                else:
                    await make_queue.put(pizza)
                    await async_sleep(0.1)

            elif not fridge_queue.empty():
                pizza = await fridge_queue.get()
                if pizza.type == self.specialist_type:
                    await self.get_ingredients_from_fridge(pizza)
                else:
                    await fridge_queue.put(pizza)
                    await async_sleep(0.1)

            else:
                self.active_pizza = None
                await async_sleep(0.1)


class Oven:
    async def do_the_job(self):
        while True:
            if not oven_queue.empty():
                pizza = await oven_queue.get()
                await async_sleep(4)
                pizza.status = 'baked'
                await take_out_of_oven_queue.put(pizza)
            else:
                await async_sleep(0.1)


fridge_queue = Queue()
make_queue = Queue()
urgent_oven_queue = Queue()
normal_oven_queue = Queue()
take_out_of_oven_queue = Queue()
pack_queue = Queue()
deliver_queue = Queue()
oven_queue = Queue()


async def console_job(pizzas, specialists):
    while True:
        print('\033[H\033[J')
        for pizza in pizzas:
            active_worker = next((s for s in specialists if s.active_pizza == pizza), None)
            status_order = Pizza.STATUSES.index(pizza.status)

            print(
                f'Pizza {pizza.pizza} ({pizza.type}, {pizza.priority}): {"*" * status_order}{"-" * (len(Pizza.STATUSES) - status_order - 1)}',
                end=''
            )
            print(f' ({pizza.status})', end='')
            if active_worker:
                print(f' (Specialist {active_worker.number}: {active_worker.specialist_type})', end='')
            print()

        if all(pizza.status == 'delivered' for pizza in pizzas):
            print("\n\033[92mAll pizzas are delivered! \033[91mДе мої гроші???\033[0m")
            break

        await async_sleep(1)


async def main():
    print("Welcome to the pizza factory!")
    ovens_amount = int(input('Enter the amount of ovens: '))

    pizza_counts = {
        'Margherita': int(input('Enter the number of Margherita pizzas: ')),
        'Pepperoni': int(input('Enter the number of Pepperoni pizzas: ')),
        'Veggie': int(input('Enter the number of Veggie pizzas: '))
    }

    priorities = {}
    specialists_counts = {}

    for pizza_type in pizza_counts:
        if pizza_counts[pizza_type] == 0:

            priorities[pizza_type] = 'Normal'  # Default priority if not specified
            specialists_counts[pizza_type] = 0  # No specialists needed
            continue

        while True:
            priority = input(f'Enter priority for {pizza_type} pizzas (0 for Normal, 1 for Urgent): ').strip()
            if priority in ['0', '1']:
                priorities[pizza_type] = 'Urgent' if priority == '1' else 'Normal'
                break
            print("Invalid input. Please enter '0' for Normal or '1' for Urgent.")

        specialists_count = int(input(f'Enter the number of {pizza_type} specialists: '))
        idiot_count = 0
        while True:
            if specialists_count < 1 and pizza_counts[pizza_type] > 0:
                print("You should enter at least one specialist.")
                specialists_count = int(input(f'Enter the number of {pizza_type} specialists: '))
            else:
                break
            idiot_count += 1
            if idiot_count == 2:
                print("\033[91mYou are bad manager. I will choose one specialist for you.\033[0m")
                specialists_count = 1
                break

        specialists_counts[pizza_type] = specialists_count

    ovens_semaphore = Semaphore(ovens_amount)
    ovens = [Oven() for _ in range(ovens_amount)]
    specialists = [
        PizzaSpecialist(pizza_type, i + 1)
        for pizza_type, count in specialists_counts.items()
        for i in range(count)
    ]

    specialist_tasks = [asyncio.create_task(specialist.do_the_job(ovens_semaphore)) for specialist in specialists]
    oven_tasks = [asyncio.create_task(oven.do_the_job()) for oven in ovens]

    pizzas = [
        Pizza(i + 1, pizza_type, priority=priorities[pizza_type])
        for pizza_type, count in pizza_counts.items()
        for i in range(count)
    ]

    fridge_tasks = [fridge_queue.put(pizza) for pizza in pizzas]
    console_task = asyncio.create_task(console_job(pizzas, specialists))

    await asyncio.gather(*fridge_tasks)
    await make_queue.join()
    await fridge_queue.join()
    await urgent_oven_queue.join()
    await normal_oven_queue.join()
    await take_out_of_oven_queue.join()
    await oven_queue.join()
    await pack_queue.join()
    await deliver_queue.join()

    for task in specialist_tasks + oven_tasks + [console_task]:
        task.cancel()

    await asyncio.gather(*specialist_tasks, *oven_tasks, console_task)


if __name__ == '__main__':
    asyncio.run(main())
