import asyncio

from asyncio import sleep as async_sleep, Lock, Queue, Semaphore


class Pizza:
    PIZZA_TYPES = {
        "Margherita": {"make": 2, "bake": 3, "pack": 1},
        "Pepperoni": {"make": 3, "bake": 4, "pack": 2},
        "Veggie": {"make": 4, "bake": 5, "pack": 2}
    }
    
    def __init__(self, pizza, type='Pepperoni', priority='Normal'):
        self.pizza = pizza
        self.type = type
        self.priority = priority
        self.status = 'in_fridge'
        self.preparation_times = Pizza.PIZZA_TYPES[type]
    
    STATUSES = (
        'in_fridge',
        'to_make',
        'made',
        'in_oven',
        'baked',
        'to_pack',
        'to_deliver',
        'delivered'
    )


class PizzaMaker:
    def __init__(self, number):
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
        if pizza.priority == "Urgent":
            make_queue._queue.appendleft(pizza)
        else:
            await make_queue.put(pizza)

    async def make_pizza(self, pizza):
        await self.make_busy(pizza.preparation_times['make'], pizza)
        pizza.status = 'made'
        await put_into_oven_queue.put(pizza)
        
    async def make_certain_pizza(self, pizza):
        if pizza.type not in self.specialties:
            return 'Specialist cannot make this pizza type'
        await self.make_busy(pizza.preparation_times["make"], pizza)
        pizza.status = 'made'
        await put_into_oven_queue.put(pizza)

    async def put_into_oven(self, pizza, ovens_semaphore):
        await ovens_semaphore.acquire()
        await self.make_busy(1, pizza)
        pizza.status = 'in_oven'
        await oven_queue.put(pizza)

    async def take_out_of_oven(self, pizza, ovens_semaphore):
        await self.make_busy(1, pizza)
        ovens_semaphore.release()
        pizza.status = 'to_pack'
        await pack_queue.put(pizza)

    async def pack_pizza(self, pizza):
        await self.make_busy(1, pizza)
        pizza.status = 'to_deliver'
        await deliver_queue.put(pizza)

    async def deliver_pizza(self, pizza):
        await self.make_busy(1, pizza)
        pizza.status = 'delivered'

    async def do_the_job(self, ovens_semaphore):
        while True:
            if not deliver_queue.empty():
                pizza = await deliver_queue.get()
                await self.deliver_pizza(pizza)
            elif not pack_queue.empty():
                pizza = await pack_queue.get()
                await self.pack_pizza(pizza)
            elif not take_out_of_oven_queue.empty():
                pizza = await take_out_of_oven_queue.get()
                await self.take_out_of_oven(pizza, ovens_semaphore)
            elif not put_into_oven_queue.empty() and not ovens_semaphore.locked():
                pizza = await put_into_oven_queue.get()
                await self.put_into_oven(pizza, ovens_semaphore)
            elif not make_queue.empty():
                pizza = await make_queue.get()
                await self.make_pizza(pizza)
            elif not fridge_queue.empty():
                pizza = await fridge_queue.get()
                await self.get_ingredients_from_fridge(pizza)
            else:
                self.active_pizza = None
                await async_sleep(1)

class PizzaSpecialist(PizzaMaker):
    def __init__(self, number, specialties):
        super().__init__(number)
        self.specialties = specialties

    async def make_pizza(self, pizza):
        if pizza.type not in self.specialties:
            print(f"Specialist {self.number} cannot make {pizza.type}.")
            return
        await super().make_pizza(pizza)
        
class Oven:
    def __init__(self):
        self.lock = Lock()

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
put_into_oven_queue = Queue()
take_out_of_oven_queue = Queue()
pack_queue = Queue()
deliver_queue = Queue()

oven_queue = Queue()


async def console_job(pizzas, workers):
    while True:
        # Clear the console
        print('\033[H\033[J')
        for pizza in pizzas:
            active_worker = next((worker for worker in workers if worker.active_pizza == pizza), None)
            status_order = Pizza.STATUSES.index(pizza.status)

            print(f'Pizza {pizza.pizza}: Priority: {pizza.priority}, type: {pizza.type}, {"*" * status_order}{"-" * (len(Pizza.STATUSES) - status_order - 1)}', end='')
            print(f' ({pizza.status})', end='')
            if active_worker:
                role = "Specialist" if isinstance(active_worker, PizzaSpecialist) else "Worker"
                specialties = f"(Specialty: {', '.join(active_worker.specialties)})" if role == "Specialist" else ""
                print(f' ({role} {active_worker.number} {specialties})', end='')
            print()
        print()
        await async_sleep(1)


async def main():
    print("Welcome to the pizza factory!")
    workers_amount = int(input('Enter the amount of workers: '))
    pizza_amount = int(input('Enter the amount of pizzas: '))
    ovens_amount = int(input('Enter the amount of ovens: '))

    ovens = [Oven() for _ in range(ovens_amount)]
    ovens_semaphore = Semaphore(ovens_amount)
    workers = [PizzaMaker(i+1) for i in range(workers_amount)]

    worker_tasks = [asyncio.create_task(worker.do_the_job(ovens_semaphore)) for worker in workers]
    oven_tasks = [asyncio.create_task(oven.do_the_job()) for oven in ovens]

    pizzas = [Pizza(i+1) for i in range(pizza_amount)]

    fridge_tasks = [fridge_queue.put(pizza) for pizza in pizzas]

    console_task = asyncio.create_task(console_job(pizzas, workers))

    await asyncio.gather(*fridge_tasks)

    await make_queue.join()
    await fridge_queue.join()
    await put_into_oven_queue.join()
    await take_out_of_oven_queue.join()
    await oven_queue.join()
    await pack_queue.join()
    await deliver_queue.join()

    for worker_task in worker_tasks:
        worker_task.cancel()

    for oven_task in oven_tasks:
        oven_task.cancel()

    console_task.cancel()

    await asyncio.gather(*worker_tasks)
    await asyncio.gather(*oven_tasks)
    await console_task


if __name__ == '__main__':
    asyncio.run(main())
